# backend/app/api/projects.py
"""Project API Routes"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from datetime import datetime
import time
import asyncio
import re
import logging
from pathlib import Path
from moviepy import AudioFileClip, VideoFileClip, concatenate_audioclips

from app.database import get_db, SessionLocal
from app.models.project import Project
from app.models.script import Script
from app.models.script_history import ScriptHistory
from app.schemas.script import ScriptSegment
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.script_generator import ScriptGenerator
from app.services.quality_detector import get_quality_detector
from app.services.visual_planner import VisualPlanner
from app.services.tts import tts_manager
from app.services.video_synthesizer import VideoSynthesizer
from app.services.video_shot_timeline import (
    load_project_materials_for_video,
    visual_shots_from_project_meta,
    build_visual_shot_timeline,
    build_ltx2_text_shot_timeline,
    narration_lines_for_shots,
)
from app.services.ltx2_video import ltx2_t2v_available
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
WORKFLOW_STEPS = ["script", "review", "visual", "audio", "video"]
OUTLINE_LLM_TIMEOUT_SEC = 90
FULL_SCRIPT_LLM_TIMEOUT_SEC = 150
STEP_ACTIVITY_LOG_MAX = 400


def _ensure_script_history_table(db: Session) -> None:
    """Ensure script history table exists for old databases without migration."""
    bind = db.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(ScriptHistory.__tablename__):
        ScriptHistory.__table__.create(bind=bind, checkfirst=True)


def _create_script_snapshot(db: Session, script: Script, project_id: str, source: str) -> None:
    """Persist script snapshot to history table."""
    _ensure_script_history_table(db)
    db.add(ScriptHistory(
        script_id=script.id,
        project_id=project_id,
        version=script.version or 1,
        outline=script.outline,
        full_script=script.full_script,
        segments=script.segments,
        source=source
    ))
    db.flush()
    _prune_script_history(db, project_id, keep=10)


def _prune_script_history(db: Session, project_id: str, keep: int = 10) -> None:
    """Keep only latest N history records for one project."""
    if keep <= 0:
        return
    stale_records = (
        db.query(ScriptHistory)
        .filter(ScriptHistory.project_id == project_id)
        .order_by(ScriptHistory.created_at.desc(), ScriptHistory.id.desc())
        .offset(keep)
        .all()
    )
    for item in stale_records:
        db.delete(item)


def _init_steps(project_metadata: Optional[dict]) -> dict:
    """Initialize workflow steps in metadata if not present."""
    metadata = dict(project_metadata or {})
    existing_steps = metadata.get("steps") if isinstance(metadata.get("steps"), dict) else {}

    steps = {}
    for step in WORKFLOW_STEPS:
        step_data = existing_steps.get(step, {})
        steps[step] = {
            "status": step_data.get("status", "wait"),
            "output": step_data.get("output"),
            "updated_at": step_data.get("updated_at")
        }

    metadata["steps"] = steps
    return metadata


def _split_text_for_tts(text: str, max_chars: int = 380) -> List[str]:
    """Split long script text into TTS-friendly chunks by sentence boundaries."""
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return []

    # Prefer sentence-level split in Chinese/English punctuation.
    sentences = re.split(r"(?<=[。！？!?；;])\s*", normalized)
    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # Very long sentence fallback: hard split.
        while len(sentence) > max_chars:
            part = sentence[:max_chars]
            sentence = sentence[max_chars:]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(part)

        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def _build_tts_clean_text(script_text: str) -> str:
    """Extract narration-only text for TTS and remove production annotations."""
    raw = str(script_text or "").replace("\r", "\n")
    if not raw.strip():
        return ""

    # Prefer explicit narration lines if available.
    narration_hits = re.findall(r"旁白[：:]\s*([^\n]+)", raw)
    narration_lines = []
    for line in narration_hits:
        txt = str(line).strip().strip('"').strip("“”")
        if txt:
            narration_lines.append(txt)
    if narration_lines:
        return re.sub(r"\s+", " ", " ".join(narration_lines)).strip()

    # Fallback: remove common production labels and metadata lines.
    cleaned_lines: List[str] = []
    skip_keywords = [
        "镜头", "时长", "景别", "机位", "运镜", "画面与动作", "字幕", "音乐/音效",
        "剪辑提示", "导演提示", "后期与剪辑建议", "封面", "目标受众", "核心卖点",
        "情绪曲线", "对标账号风格关键词", "互动", "风险与合规", "素材建议"
    ]
    for raw_line in raw.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-•\d\.\)\(]+", "", line).strip()
        if any(key in line for key in skip_keywords):
            continue
        # Remove bracket titles like 【视频定位】
        line = re.sub(r"【[^】]{1,30}】", "", line).strip()
        if len(line) < 4:
            continue
        cleaned_lines.append(line)

    return re.sub(r"\s+", " ", " ".join(cleaned_lines)).strip()


def _concat_audio_segments(segment_files: List[Path], output_file: Path) -> float:
    """Merge multiple audio segment files into one and return total duration."""
    if not segment_files:
        raise ValueError("No audio segments to merge")
    if len(segment_files) == 1:
        segment_files[0].replace(output_file)
        clip = AudioFileClip(str(output_file))
        try:
            return float(clip.duration or 0)
        finally:
            clip.close()

    clips = [AudioFileClip(str(p)) for p in segment_files]
    merged = concatenate_audioclips(clips)
    try:
        merged.write_audiofile(str(output_file), fps=44100, logger=None)
        duration = float(merged.duration or 0)
    finally:
        for c in clips:
            c.close()
        merged.close()
    for p in segment_files:
        if p.exists():
            p.unlink(missing_ok=True)
    return duration


def _attach_audio_to_video(video_path: Path, audio_path: Path, output_path: Path) -> float:
    """Attach audio track to video and return final duration."""
    video_clip = VideoFileClip(str(video_path))
    audio_clip = AudioFileClip(str(audio_path))
    mixed = None
    try:
        if audio_clip.duration > video_clip.duration:
            # MoviePy 2.x：AudioFileClip 使用 subclipped
            audio_clip = audio_clip.subclipped(0, video_clip.duration)
        # MoviePy 2.x：使用 with_audio 替代已移除的 set_audio
        mixed = video_clip.with_audio(audio_clip)
        mixed.write_videofile(
            str(output_path),
            fps=int(video_clip.fps or 24),
            codec="libx264",
            audio_codec="aac",
            logger=None
        )
        return float(video_clip.duration or 0)
    finally:
        if mixed:
            mixed.close()
        audio_clip.close()
        video_clip.close()


def _set_step_progress(
    project: Project,
    metadata: dict,
    step_name: str,
    db: Session,
    *,
    status: Optional[str] = None,
    percent: Optional[int] = None,
    stage: Optional[str] = None,
    message: Optional[str] = None,
    output: Optional[dict] = None,
    llm_call: Optional[dict] = None,
    reset_activity_log: bool = False,
    log_append: Optional[Union[str, List[str]]] = None,
    log_level: str = "info",
) -> None:
    """Persist real-time step progress so frontend can poll and render actual status."""
    def _parse_iso(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _seconds_between(start_iso: Optional[str], end_iso: Optional[str]) -> Optional[int]:
        start_dt = _parse_iso(start_iso)
        end_dt = _parse_iso(end_iso)
        if not start_dt or not end_dt:
            return None
        seconds = int((end_dt - start_dt).total_seconds())
        return max(0, seconds)

    # 其它 Session（如 _merge_ltx_shot_board、分镜进度回调）已 commit 时，传入的 metadata 可能陈旧，先从 DB 同步
    try:
        db.refresh(project)
        fresh = dict(project.project_metadata or {})
        metadata.clear()
        metadata.update(fresh)
    except Exception:
        pass

    steps = metadata.setdefault("steps", {})
    step = dict(steps.get(step_name) or {})
    now = datetime.now().isoformat()

    if status is not None:
        step["status"] = status
    step["updated_at"] = now
    if output is not None:
        step["output"] = output

    progress = dict(step.get("progress") or {})
    if percent is not None:
        progress["percent"] = max(0, min(100, int(percent)))
    current_stage = progress.get("stage")
    timeline = list(progress.get("timeline") or [])
    if stage is not None:
        # Close previous stage if changed.
        if current_stage and current_stage != stage and timeline:
            last = dict(timeline[-1])
            if not last.get("exited_at"):
                last["exited_at"] = now
                duration = _seconds_between(last.get("entered_at"), last.get("exited_at"))
                if duration is not None:
                    last["duration_sec"] = duration
                timeline[-1] = last
        # Open current stage if needed.
        if not timeline or timeline[-1].get("stage") != stage:
            timeline.append({
                "stage": stage,
                "entered_at": now,
                "exited_at": None
            })
        progress["stage"] = stage
    if message is not None:
        progress["message"] = message
    if not progress.get("started_at"):
        progress["started_at"] = now
    llm_calls = list(progress.get("llm_calls") or [])
    if llm_call is not None:
        call_record = dict(llm_call)
        if "recorded_at" not in call_record:
            call_record["recorded_at"] = now
        llm_calls.append(call_record)
    if llm_calls:
        progress["llm_calls"] = llm_calls
    progress["timeline"] = timeline
    if status == "completed":
        if timeline:
            last = dict(timeline[-1])
            if not last.get("exited_at"):
                last["exited_at"] = now
                duration = _seconds_between(last.get("entered_at"), last.get("exited_at"))
                if duration is not None:
                    last["duration_sec"] = duration
                timeline[-1] = last
            progress["timeline"] = timeline
        progress["finished_at"] = now
        total_duration = _seconds_between(progress.get("started_at"), progress.get("finished_at"))
        if total_duration is not None:
            progress["total_duration_sec"] = total_duration
    else:
        # Real-time total duration while still running.
        total_duration = _seconds_between(progress.get("started_at"), now)
        if total_duration is not None:
            progress["total_duration_sec"] = total_duration
    progress["updated_at"] = now

    # 活动日志：供前端视频步轮询展示（有上限，避免 metadata 膨胀）
    if reset_activity_log or log_append is not None:
        logs = [] if reset_activity_log else list(progress.get("activity_log") or [])
        if log_append is not None:
            lvl = str(log_level or "info").lower()[:16]
            chunks = log_append if isinstance(log_append, list) else [log_append]
            for raw in chunks:
                text = str(raw).strip()
                if not text:
                    continue
                logs.append({"at": now, "level": lvl, "message": text[:4000]})
        if len(logs) > STEP_ACTIVITY_LOG_MAX:
            logs = logs[-STEP_ACTIVITY_LOG_MAX :]
        progress["activity_log"] = logs
    if reset_activity_log:
        progress["ltx_shots"] = []
        progress["ltx_shots_completed"] = 0
        progress["ltx_shots_total"] = 0

    step["progress"] = progress

    steps[step_name] = step
    metadata["steps"] = steps
    project.current_step = step_name
    project.project_metadata = metadata
    db.commit()


def _merge_ltx_shot_board(project_id: str, step_name: str, detail: dict) -> None:
    """LTX 分镜：写入 progress.ltx_shots，供前端分开展示每镜输入与输出并刷新进度。"""
    if not isinstance(detail, dict):
        return
    sdb = SessionLocal()
    try:
        proj = sdb.query(Project).filter(Project.id == project_id).first()
        if not proj:
            return
        meta = dict(proj.project_metadata or {})
        steps = dict(meta.get("steps") or {})
        step = dict(steps.get(step_name) or {})
        progress = dict(step.get("progress") or {})
        shots = list(progress.get("ltx_shots") or [])
        idx = int(detail.get("shot_index", 0))
        total = int(detail.get("total") or 0)
        while len(shots) <= idx:
            shots.append(
                {
                    "shot_index": len(shots),
                    "status": "pending",
                    "total": total,
                }
            )
        row = dict(shots[idx])
        row["shot_index"] = idx
        row["total"] = total
        if detail.get("shot_no") is not None:
            row["shot_no"] = detail.get("shot_no")
        ev = str(detail.get("event") or "")
        if ev == "start":
            row["status"] = "generating"
            row["prompt"] = str(detail.get("prompt") or "")[:12000]
            row["narration"] = str(detail.get("narration") or "")[:12000]
            row["duration_sec"] = detail.get("duration_sec")
            row.pop("output_path", None)
            row.pop("size_kb", None)
        elif ev == "complete":
            row["status"] = "done" if detail.get("ok") else "placeholder"
            op = detail.get("output_path")
            if op:
                row["output_path"] = str(op)[:2000]
            row["size_kb"] = detail.get("size_kb")
        shots[idx] = row
        progress["ltx_shots"] = shots
        done = sum(1 for s in shots if s.get("status") in ("done", "placeholder"))
        progress["ltx_shots_completed"] = done
        progress["ltx_shots_total"] = total
        step["progress"] = progress
        steps[step_name] = step
        meta["steps"] = steps
        proj.project_metadata = meta
        sdb.commit()
    finally:
        sdb.close()


def _append_step_activity_log(
    project_id: str,
    step_name: str,
    message: str,
    *,
    level: str = "info",
) -> None:
    """独立 Session：线程或异步路径中追加步骤活动日志，并写一条标准 logger。"""
    text = (message or "").strip()
    if not text:
        return
    logger.info("[workflow activity] project=%s step=%s %s", project_id, step_name, text[:800])
    sdb = SessionLocal()
    try:
        proj = sdb.query(Project).filter(Project.id == project_id).first()
        if not proj:
            return
        meta = dict(proj.project_metadata or {})
        _set_step_progress(
            proj,
            meta,
            step_name,
            sdb,
            log_append=text,
            log_level=level,
        )
    finally:
        sdb.close()


def _video_synth_progress_callback(project_id: str, step_name: str):
    """MoviePy / 时间轴处理期间节流写入步骤进度（独立 Session，避免阻塞主请求会话）。"""
    last_emit = [0.0, -1]
    last_log_msg = [""]

    def cb(raw_percent: int, msg: str) -> None:
        now = time.monotonic()
        if now - last_emit[0] < 1.5 and abs(int(raw_percent) - last_emit[1]) < 6:
            return
        last_emit[0] = now
        last_emit[1] = int(raw_percent)
        try:
            rp = float(raw_percent)
            mapped = int(max(56, min(91, 56 + (rp - 25) * (35.0 / 65.0))))
        except Exception:
            mapped = 72
        m = (msg or "视频合成中")[:220]
        log_line = None
        if m and m != last_log_msg[0]:
            last_log_msg[0] = m
            log_line = m[:900]
        sdb = SessionLocal()
        try:
            proj = sdb.query(Project).filter(Project.id == project_id).first()
            if not proj:
                return
            meta = dict(proj.project_metadata or {})
            _set_step_progress(
                proj,
                meta,
                step_name,
                sdb,
                status="processing",
                percent=mapped,
                stage="video_synthesizing",
                message=m,
                log_append=log_line,
            )
        finally:
            sdb.close()

    return cb


def _video_shot_timeline_progress_factory(project_id: str, step_name: str):
    """分镜时间轴（LTX / 素材裁切等）每镜进度回调。"""

    async def on_shot(idx: int, total: int, msg: str) -> None:
        sdb = SessionLocal()
        try:
            proj = sdb.query(Project).filter(Project.id == project_id).first()
            if not proj:
                return
            meta = dict(proj.project_metadata or {})
            pct = 20 + int((idx / max(total, 1)) * 28)
            _set_step_progress(
                proj,
                meta,
                step_name,
                sdb,
                status="processing",
                percent=min(48, max(18, pct)),
                stage="video_shot_timeline",
                message=msg[:220],
                log_append=msg[:900],
            )
        finally:
            sdb.close()

    return on_shot


def _build_review_segments(full_script: str, raw_segments: Optional[list]) -> List[ScriptSegment]:
    """Build ScriptSegment list for quality review."""
    segments: List[ScriptSegment] = []
    for idx, item in enumerate(raw_segments or []):
        if not isinstance(item, dict):
            continue
        try:
            segments.append(ScriptSegment(
                id=str(item.get("id") or f"seg-{idx + 1}"),
                text=str(item.get("text") or ""),
                duration=float(item.get("duration") or 0),
                emotion=item.get("emotion"),
                material_ids=item.get("material_ids") or []
            ))
        except Exception:
            continue

    # If segments are missing, build simple fallback segments from paragraphs.
    if segments:
        return segments

    parts = [p.strip() for p in str(full_script or "").split("\n") if p.strip()]
    if not parts:
        return []

    preview_parts = parts[:10]
    avg_duration = max(6.0, min(12.0, 90.0 / max(1, len(preview_parts))))
    for idx, text in enumerate(preview_parts):
        segments.append(ScriptSegment(
            id=f"fallback-seg-{idx + 1}",
            text=text,
            duration=avg_duration,
            emotion="neutral",
            material_ids=[]
        ))
    return segments


class BatchDeleteRequest(BaseModel):
    project_ids: List[str]


class BatchUpdateStatusRequest(BaseModel):
    project_ids: List[str]
    status: str


class StepExecuteRequest(BaseModel):
    outline_prompt: Optional[str] = None
    full_script_prompt: Optional[str] = None


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[str] = Query(
        None,
        description="Filter by project status"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of projects to skip"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of projects to return"
    ),
    db: Session = Depends(get_db)
):
    """
    List projects with optional filtering and pagination

    Args:
        status: Optional status filter
        offset: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of projects
    """
    query = db.query(Project)

    if status:
        query = query.filter(Project.status == status)

    query = query.order_by(Project.created_at.desc())
    projects = query.offset(offset).limit(limit).all()

    # Map project_metadata to metadata for response
    result = []
    for project in projects:
        project_dict = {
            "id": project.id,
            "title": project.title,
            "status": project.status,
            "current_step": project.current_step,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "topic_source": project.topic_source,
            "topic_title": project.topic_title,
            "topic_hot_score": project.topic_hot_score,
            "metadata": project.project_metadata
        }
        result.append(ProjectResponse(**project_dict))

    return result


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new project

    Args:
        project_in: Project creation data
        db: Database session

    Returns:
        Created project
    """
    project = Project(
        title=project_in.title,
        topic_source=project_in.topic_source,
        topic_title=project_in.topic_title,
        topic_hot_score=project_in.topic_hot_score,
        project_metadata=project_in.metadata,
        status="pending",
        current_step="topic_selection"
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Map project_metadata to metadata for response
    project_dict = {
        "id": project.id,
        "title": project.title,
        "status": project.status,
        "current_step": project.current_step,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "topic_source": project.topic_source,
        "topic_title": project.topic_title,
        "topic_hot_score": project.topic_hot_score,
        "metadata": project.project_metadata
    }

    return ProjectResponse(**project_dict)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a project by ID

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        Project data

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Map project_metadata to metadata for response
    project_dict = {
        "id": project.id,
        "title": project.title,
        "status": project.status,
        "current_step": project.current_step,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "topic_source": project.topic_source,
        "topic_title": project.topic_title,
        "topic_hot_score": project.topic_hot_score,
        "metadata": project.project_metadata
    }

    return ProjectResponse(**project_dict)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a project

    Args:
        project_id: The project ID
        project_in: Project update data
        db: Database session

    Returns:
        Updated project

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update fields if provided
    if project_in.title is not None:
        project.title = project_in.title
    if project_in.status is not None:
        project.status = project_in.status
    if project_in.current_step is not None:
        project.current_step = project_in.current_step
    if project_in.metadata is not None:
        project.project_metadata = project_in.metadata

    db.commit()
    db.refresh(project)

    # Map project_metadata to metadata for response
    project_dict = {
        "id": project.id,
        "title": project.title,
        "status": project.status,
        "current_step": project.current_step,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "topic_source": project.topic_source,
        "topic_title": project.topic_title,
        "topic_hot_score": project.topic_hot_score,
        "metadata": project.project_metadata
    }

    return ProjectResponse(**project_dict)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    return {"success": True, "message": "Project deleted successfully"}


@router.post("/batch/delete")
async def batch_delete_projects(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量删除项目"""
    if not request.project_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_ids cannot be empty"
        )

    # 只删除用户自己的项目
    deleted = db.query(Project).filter(
        Project.id.in_(request.project_ids),
        Project.owner_id == current_user.id
    ).delete(synchronize_session=False)

    db.commit()

    return {"deleted_count": deleted}


@router.post("/batch/update-status")
async def batch_update_project_status(
    request: BatchUpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量更新项目状态"""
    if not request.project_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_ids cannot be empty"
        )

    # 只更新用户自己的项目
    projects = db.query(Project).filter(
        Project.id.in_(request.project_ids),
        Project.owner_id == current_user.id
    ).all()

    for project in projects:
        project.status = request.status

    db.commit()

    return {"updated_count": len(projects)}


@router.post("/{project_id}/steps/{step_name}/execute")
async def execute_project_step(
    project_id: str,
    step_name: str,
    request: Optional[StepExecuteRequest] = None,
    db: Session = Depends(get_db)
):
    """Execute a workflow step for the project."""
    if step_name not in WORKFLOW_STEPS:
        raise HTTPException(status_code=400, detail=f"Unsupported step: {step_name}")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = _init_steps(project.project_metadata)
    try:
        _set_step_progress(
            project,
            metadata,
            step_name,
            db,
            status="processing",
            percent=5,
            stage="queued",
            message="任务已提交，等待执行"
        )

        output = None
        if step_name == "script":
            topic = project.topic_title or project.title
            generator = ScriptGenerator()
            outline_prompt = request.outline_prompt.strip() if request and request.outline_prompt else generator.build_outline_prompt(topic=topic)
            try:
                _set_step_progress(
                    project,
                    metadata,
                    step_name,
                    db,
                    status="processing",
                    percent=20,
                    stage="outline_generating",
                    message="正在生成脚本大纲"
                )
                outline_llm_start = time.perf_counter()
                try:
                    outline = await asyncio.wait_for(
                        generator.generate_outline(topic, custom_prompt=outline_prompt),
                        timeout=OUTLINE_LLM_TIMEOUT_SEC
                    )
                    outline_llm_duration = round(time.perf_counter() - outline_llm_start, 2)
                    _set_step_progress(
                        project,
                        metadata,
                        step_name,
                        db,
                        llm_call={
                            "stage": "outline_generating",
                            "provider": generator.provider_name,
                            "duration_sec": outline_llm_duration,
                            "success": True,
                            "input": outline_prompt
                        }
                    )
                except Exception as outline_exc:
                    outline_llm_duration = round(time.perf_counter() - outline_llm_start, 2)
                    _set_step_progress(
                        project,
                        metadata,
                        step_name,
                        db,
                        llm_call={
                            "stage": "outline_generating",
                            "provider": generator.provider_name,
                            "duration_sec": outline_llm_duration,
                            "success": False,
                            "error": str(outline_exc),
                            "input": outline_prompt
                        }
                    )
                    raise

                _set_step_progress(
                    project,
                    metadata,
                    step_name,
                    db,
                    status="processing",
                    percent=45,
                    stage="outline_done",
                    message="大纲已生成，正在构建完整脚本"
                )
                full_script_prompt = (
                    request.full_script_prompt.strip()
                    if request and request.full_script_prompt
                    else generator.build_full_script_prompt(outline=outline, topic=topic)
                )

                _set_step_progress(
                    project,
                    metadata,
                    step_name,
                    db,
                    status="processing",
                    percent=65,
                    stage="script_generating",
                    message="正在生成完整脚本与分镜细节"
                )
                full_script_llm_start = time.perf_counter()
                try:
                    full_result = await asyncio.wait_for(
                        generator.generate_full_script(outline, topic, custom_prompt=full_script_prompt),
                        timeout=FULL_SCRIPT_LLM_TIMEOUT_SEC
                    )
                    full_script_llm_duration = round(time.perf_counter() - full_script_llm_start, 2)
                    _set_step_progress(
                        project,
                        metadata,
                        step_name,
                        db,
                        llm_call={
                            "stage": "script_generating",
                            "provider": generator.provider_name,
                            "duration_sec": full_script_llm_duration,
                            "success": True,
                            "input": full_script_prompt
                        }
                    )
                except Exception as full_script_exc:
                    full_script_llm_duration = round(time.perf_counter() - full_script_llm_start, 2)
                    _set_step_progress(
                        project,
                        metadata,
                        step_name,
                        db,
                        llm_call={
                            "stage": "script_generating",
                            "provider": generator.provider_name,
                            "duration_sec": full_script_llm_duration,
                            "success": False,
                            "error": str(full_script_exc),
                            "input": full_script_prompt
                        }
                    )
                    raise
                full_script = full_result["full_script"]
                segments = [seg.model_dump() for seg in full_result["segments"]]

                _set_step_progress(
                    project,
                    metadata,
                    step_name,
                    db,
                    status="processing",
                    percent=85,
                    stage="persisting",
                    message="正在保存脚本与版本记录"
                )

                script = db.query(Script).filter(Script.project_id == project_id).first()
                if not script:
                    script = Script(
                        project_id=project_id,
                        outline=outline,
                        full_script=full_script,
                        segments=segments,
                        version=1,
                        is_approved=False
                    )
                    db.add(script)
                else:
                    script.outline = outline
                    script.full_script = full_script
                    script.segments = segments
                    script.version = (script.version or 1) + 1
                db.flush()

                output = {
                    "topic": topic,
                    "llm_input": {
                        "outline_prompt": outline_prompt,
                        "full_script_prompt": full_script_prompt
                    },
                    "outline": outline,
                    "full_script": full_script,
                    "segments_count": len(segments),
                    "fallback": False
                }
                _create_script_snapshot(db, script, project_id, source="llm_generate")
            except Exception as exc:
                # Fallback output lets local development run without LLM keys.
                _set_step_progress(
                    project,
                    metadata,
                    step_name,
                    db,
                    status="processing",
                    percent=70,
                    stage="fallback_generating",
                    message="模型调用失败，正在生成离线占位结果"
                )
                outline = f"1. 开场引入：{topic}\n2. 核心观点展开\n3. 结尾总结与互动引导"
                full_script_prompt = (
                    request.full_script_prompt.strip()
                    if request and request.full_script_prompt
                    else generator.build_full_script_prompt(outline=outline, topic=topic)
                )
                full_script = (
                    f"大家好，今天我们聊聊「{topic}」。\n"
                    "先用一个常见场景切入，再给出3个可执行的方法，"
                    "最后做总结并邀请大家评论区交流。"
                )
                script = db.query(Script).filter(Script.project_id == project_id).first()
                if not script:
                    script = Script(
                        project_id=project_id,
                        outline=outline,
                        full_script=full_script,
                        segments=[],
                        version=1,
                        is_approved=False
                    )
                    db.add(script)
                else:
                    script.outline = outline
                    script.full_script = full_script
                    script.segments = []
                    script.version = (script.version or 1) + 1
                db.flush()

                output = {
                    "topic": topic,
                    "llm_input": {
                        "outline_prompt": outline_prompt,
                        "full_script_prompt": full_script_prompt
                    },
                    "outline": outline,
                    "full_script": full_script,
                    "segments_count": 0,
                    "fallback": True,
                    "reason": str(exc)
                }
                _create_script_snapshot(db, script, project_id, source="fallback_generate")
        elif step_name == "review":
            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=25,
                stage="review_loading",
                message="正在读取脚本内容"
            )
            script = db.query(Script).filter(Script.project_id == project_id).first()
            if not script or not (script.full_script or "").strip():
                raise ValueError("未找到可审核的完整脚本，请先执行脚本生成")

            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=55,
                stage="review_analyzing",
                message="正在进行脚本质量审核"
            )
            detector = get_quality_detector()
            review_segments = _build_review_segments(script.full_script or "", script.segments if isinstance(script.segments, list) else [])
            report = await detector.detect_script_quality_hybrid(
                script.full_script or "",
                review_segments,
                topic=project.topic_title or project.title
            )

            issues = []
            for issue in (report.issues or []):
                if isinstance(issue, dict):
                    issues.append({
                        "type": issue.get("type"),
                        "severity": issue.get("severity", "medium"),
                        "message": issue.get("message"),
                        "score": issue.get("score")
                    })
                else:
                    issues.append({
                        "severity": "medium",
                        "message": str(issue)
                    })

            recommendations = [str(item) for item in (report.recommendations or [])]
            overall_score = float(report.overall_score or 0)
            grade = str(report.grade or "E")
            passed = overall_score >= 75

            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=85,
                stage="review_persisting",
                message="正在整理审核报告"
            )

            output = {
                "mode": "real_review",
                "score": round(overall_score, 2),
                "grade": grade,
                "passed": passed,
                "issues_count": len(issues),
                "issues": issues,
                "recommendations": recommendations,
                "metrics": report.metrics or {},
                "reviewed_at": datetime.now().isoformat()
            }
        elif step_name == "visual":
            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=20,
                stage="visual_loading",
                message="正在读取脚本并准备视觉规划"
            )
            script = db.query(Script).filter(Script.project_id == project_id).first()
            if not script or not (script.full_script or "").strip():
                raise ValueError("未找到可规划的完整脚本，请先执行脚本生成")

            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=60,
                stage="visual_planning",
                message="正在生成分镜与视觉规划"
            )
            planner = VisualPlanner()
            plan = await planner.generate_plan(
                topic=project.topic_title or project.title,
                outline=script.outline or "",
                full_script=script.full_script or "",
                segments=script.segments if isinstance(script.segments, list) else []
            )

            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=85,
                stage="visual_structuring",
                message="正在整理视觉规划结果"
            )
            output = {
                "mode": plan.get("mode", "real_visual_plan"),
                "topic": project.topic_title or project.title,
                "summary": plan.get("summary", ""),
                "style_direction": plan.get("style_direction", ""),
                "target_duration_sec": plan.get("target_duration_sec"),
                "shots_count": len(plan.get("shots") or []),
                "shots": plan.get("shots") or [],
                "llm_input": plan.get("llm_input") or {},
                "planned_at": datetime.now().isoformat(),
                "message": plan.get("message", "视觉规划已完成")
            }
            metadata["visual_plan"] = {
                "shots": output.get("shots") or [],
                "summary": output.get("summary", ""),
                "style_direction": output.get("style_direction", ""),
                "target_duration_sec": output.get("target_duration_sec"),
                "planned_at": output.get("planned_at"),
            }
        elif step_name == "audio":
            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=20,
                stage="audio_loading",
                message="正在读取脚本并准备配音"
            )
            script = db.query(Script).filter(Script.project_id == project_id).first()
            if not script or not (script.full_script or "").strip():
                raise ValueError("未找到可配音的完整脚本，请先执行脚本生成")

            tts_text = _build_tts_clean_text(script.full_script or "")
            if not tts_text:
                tts_text = " ".join(str(script.full_script or "").split())
            if not tts_text:
                raise ValueError("脚本文本为空，无法生成音频")
            text_chunks = _split_text_for_tts(tts_text, max_chars=380)
            if not text_chunks:
                raise ValueError("脚本文本为空，无法生成音频")

            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=60,
                stage="audio_synthesizing",
                message="正在调用 TTS 生成配音"
            )

            provider_name = settings.DEFAULT_TTS_PROVIDER
            provider = tts_manager.get_provider(provider_name)

            audio_dir = (Path(settings.DATA_DIR) / "audio" / str(project_id)).resolve()
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_file = audio_dir / f"voiceover_{int(time.time())}.mp3"
            segment_dir = audio_dir / f"segments_{int(time.time())}"
            segment_dir.mkdir(parents=True, exist_ok=True)
            segment_files: List[Path] = []
            tts_voice = None
            tts_provider = provider_name
            duration_sum = 0.0
            for idx, chunk in enumerate(text_chunks, start=1):
                seg_file = segment_dir / f"seg_{idx:03d}.mp3"
                seg_result = await provider.synthesize(
                    text=chunk,
                    output_path=str(seg_file),
                    language="zh-CN",
                    speed=1.0
                )
                segment_files.append(seg_file)
                tts_provider = seg_result.get("provider", tts_provider)
                tts_voice = seg_result.get("voice", tts_voice)
                duration_sum += float(seg_result.get("duration") or 0)
                chunk_progress = 60 + int((idx / len(text_chunks)) * 20)
                _set_step_progress(
                    project,
                    metadata,
                    step_name,
                    db,
                    status="processing",
                    percent=min(chunk_progress, 80),
                    stage="audio_synthesizing",
                    message=f"正在生成配音分段 {idx}/{len(text_chunks)}"
                )

            merged_duration = _concat_audio_segments(segment_files, audio_file)
            if segment_dir.exists():
                segment_dir.rmdir()

            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=85,
                stage="audio_persisting",
                message="正在保存音频结果"
            )
            metadata = dict(project.project_metadata or {})
            metadata["audio_path"] = str(audio_file.resolve())
            metadata["audio"] = {
                "path": str(audio_file.resolve()),
                "provider": tts_provider,
                "voice": tts_voice,
                "duration_sec": round(merged_duration or duration_sum, 2),
                "chunk_count": len(text_chunks),
                "tts_input": {
                    "source_mode": "narration_first_cleaned_text",
                    "full_text": tts_text,
                    "chunk_count": len(text_chunks),
                    "chunks": text_chunks
                },
                "generated_at": datetime.now().isoformat()
            }
            project.project_metadata = metadata
            db.commit()

            output = {
                "mode": "real_audio_synthesis",
                "provider": tts_provider,
                "voice": tts_voice,
                "audio_path": str(audio_file.resolve()),
                "audio_download_url": f"/api/projects/{project_id}/steps/audio/download",
                "duration_sec": round(merged_duration or duration_sum, 2),
                "chunk_count": len(text_chunks),
                "text_length": len(tts_text),
                "tts_input": {
                    "source_mode": "narration_first_cleaned_text",
                    "full_text": tts_text,
                    "chunk_count": len(text_chunks),
                    "chunks": text_chunks
                },
                "message": "音频生成完成"
            }
        elif step_name == "video":
            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=15,
                stage="video_loading",
                message="正在读取素材与音频资源",
                reset_activity_log=True,
                log_append="视频步骤开始：加载素材、分镜与口播配置",
            )

            project_meta = dict(project.project_metadata or {})
            materials = load_project_materials_for_video(db, project_id, project_meta)
            shots = visual_shots_from_project_meta(project_meta)
            shot_stats: Optional[Dict[str, Any]] = None
            synthesis_mode = "materials_only"
            timeline: Optional[List[Dict[str, Any]]] = None
            use_ltx2_t2v = False
            ltx_shot_board: List[Any] = []
            if shots:
                shot_cb = _video_shot_timeline_progress_factory(project_id, step_name)
                if ltx2_t2v_available():
                    _set_step_progress(
                        project,
                        metadata,
                        step_name,
                        db,
                        status="processing",
                        percent=35,
                        stage="video_shot_timeline",
                        message="LTX-2：按分镜与脚本口播生成音视频片段",
                        log_append=[
                            f"素材条目 {len(materials)}；分镜 {len(shots)}；进入 LTX-2 分镜生成",
                        ],
                    )
                    narrations = narration_lines_for_shots(db, project_id, len(shots))
                    timeline, shot_stats, ltx_shot_board = await build_ltx2_text_shot_timeline(
                        shots,
                        narrations,
                        project_id=project_id,
                        on_shot_progress=shot_cb,
                        on_activity_log=lambda m: _append_step_activity_log(
                            project_id, step_name, m
                        ),
                        on_shot_board=lambda d: _merge_ltx_shot_board(
                            project_id, step_name, d
                        ),
                    )
                    synthesis_mode = "ltx2_text_shots"
                    use_ltx2_t2v = True
                else:
                    _set_step_progress(
                        project,
                        metadata,
                        step_name,
                        db,
                        status="processing",
                        percent=35,
                        stage="video_shot_timeline",
                        message="按视觉规划组装分镜时间轴（裁切素材 / 静图等）",
                        log_append=f"未启用 LTX：走视觉时间轴（素材 {len(materials)}，分镜 {len(shots)}）",
                    )
                    timeline, shot_stats = await build_visual_shot_timeline(
                        shots,
                        materials,
                        project_id=project_id,
                        on_shot_progress=shot_cb,
                    )
                    synthesis_mode = "visual_shots"
            elif not materials:
                raise ValueError("未找到可用素材，请先执行视觉规划或准备素材后再执行视频合成")

            synthesizer = VideoSynthesizer()

            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=55,
                stage="video_synthesizing",
                message="正在合成基础视频",
                log_append=(
                    f"MoviePy 拼接：时间轴 {len(timeline)} 段，素材合并 {len(materials)}"
                    if timeline is not None and len(timeline) > 0
                    else f"MoviePy 拼接：纯素材模式，素材 {len(materials)}"
                ),
            )
            synth_progress = _video_synth_progress_callback(project_id, step_name)
            base_video_path = Path(synthesizer.synthesize(
                project_id=project_id,
                materials=materials,
                progress_callback=synth_progress,
                timeline=timeline,
                log_callback=lambda m: _append_step_activity_log(project_id, step_name, m),
            )).resolve()
            if not base_video_path.exists():
                raise ValueError("视频合成失败：未产出视频文件")

            final_video_path = base_video_path
            audio_meta = project_meta.get("audio") if isinstance(project_meta.get("audio"), dict) else {}
            audio_path_value = audio_meta.get("path") or project_meta.get("audio_path")
            attached_audio = False
            skip_tts_overlay = (
                use_ltx2_t2v
                and getattr(settings, "LTX2_T2V_SKIP_EXTERNAL_TTS", True)
            )
            if audio_path_value and not skip_tts_overlay:
                audio_path = Path(str(audio_path_value)).expanduser()
                if not audio_path.is_absolute():
                    audio_path = (Path(settings.DATA_DIR) / audio_path).resolve()
                if audio_path.exists() and audio_path.is_file():
                    _set_step_progress(
                        project,
                        metadata,
                        step_name,
                        db,
                        status="processing",
                        percent=78,
                        stage="video_audio_mix",
                        message="正在挂载音频轨道",
                        log_append=f"挂载外部 TTS 音轨：{audio_path.name}",
                    )
                    final_video_path = base_video_path.parent / f"{base_video_path.stem}_with_audio.mp4"
                    _attach_audio_to_video(base_video_path, audio_path, final_video_path)
                    attached_audio = True

            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=88,
                stage="video_persisting",
                message="正在保存视频结果",
                log_append=f"写入项目元数据，成片路径已确定",
            )
            video_info = synthesizer.get_video_info(str(final_video_path))
            project_meta["video_path"] = str(final_video_path)
            project_meta["video"] = {
                "path": str(final_video_path),
                "with_audio": attached_audio,
                "duration_sec": video_info.get("duration"),
                "width": video_info.get("width"),
                "height": video_info.get("height"),
                "fps": video_info.get("fps"),
                "size": video_info.get("size"),
                "generated_at": datetime.now().isoformat(),
                "synthesis_mode": synthesis_mode,
                "shots_used": len(shots) if shots else 0,
                "shot_timeline_stats": shot_stats,
                "ltx2_t2v": use_ltx2_t2v,
                "ltx_shot_board": ltx_shot_board if use_ltx2_t2v else [],
                "ltx2_skip_external_tts": bool(
                    use_ltx2_t2v and getattr(settings, "LTX2_T2V_SKIP_EXTERNAL_TTS", True)
                ),
            }
            project.project_metadata = project_meta
            db.commit()

            output = {
                "mode": "real_video_synthesis",
                "video_path": str(final_video_path),
                "video_download_url": f"/api/projects/{project_id}/steps/video/download",
                "materials_count": len(materials),
                "with_audio": attached_audio,
                "video_info": video_info,
                "synthesis_mode": synthesis_mode,
                "shots_used": len(shots) if shots else 0,
                "shot_timeline_stats": shot_stats,
                "ltx_shot_board": ltx_shot_board if use_ltx2_t2v else [],
                "message": "视频合成完成"
            }
        else:
            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="processing",
                percent=60,
                stage="running",
                message=f"{step_name} 步骤执行中"
            )
            output = {
                "message": f"{step_name} 步骤已执行（当前为开发占位实现）"
            }

        _set_step_progress(
            project,
            metadata,
            step_name,
            db,
            status="completed",
            percent=100,
            stage="completed",
            message="处理完成",
            output=output,
            log_append="视频合成流程已全部完成" if step_name == "video" else None,
        )

        return {
            "success": True,
            "project_id": project_id,
            "step": step_name,
            "status": metadata["steps"][step_name]["status"],
            "output": output
        }
    except Exception as exc:
        # Final guard: never leave the UI hanging in processing state.
        try:
            db.rollback()
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            metadata = _init_steps(project.project_metadata)
            _set_step_progress(
                project,
                metadata,
                step_name,
                db,
                status="failed",
                stage="failed",
                message=f"执行失败：{str(exc)}",
                output={
                    "error": str(exc),
                    "failed_at": datetime.now().isoformat()
                },
                log_append=f"失败：{str(exc)}",
                log_level="error",
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Step execution failed: {str(exc)}")


@router.post("/{project_id}/steps/{step_name}/regenerate")
async def regenerate_project_step(
    project_id: str,
    step_name: str,
    request: Optional[StepExecuteRequest] = None,
    db: Session = Depends(get_db)
):
    """Regenerate a workflow step (same behavior as execute for now)."""
    return await execute_project_step(project_id=project_id, step_name=step_name, request=request, db=db)


@router.get("/{project_id}/steps/audio/download")
async def download_project_audio(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Download generated audio file for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = dict(project.project_metadata or {})
    audio_meta = metadata.get("audio") if isinstance(metadata.get("audio"), dict) else {}
    audio_path_value = audio_meta.get("path") or metadata.get("audio_path")
    if not audio_path_value:
        raise HTTPException(status_code=404, detail="Audio file not found")

    audio_path = Path(str(audio_path_value)).expanduser()
    if not audio_path.is_absolute():
        audio_path = (Path(settings.DATA_DIR) / audio_path).resolve()

    if not audio_path.exists() or not audio_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=audio_path.name
    )


@router.get("/{project_id}/steps/video/download")
async def download_project_video(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Download generated video file for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = dict(project.project_metadata or {})
    video_meta = metadata.get("video") if isinstance(metadata.get("video"), dict) else {}
    video_path_value = video_meta.get("path") or metadata.get("video_path")
    if not video_path_value:
        raise HTTPException(status_code=404, detail="Video file not found")

    video_path = Path(str(video_path_value)).expanduser()
    if not video_path.is_absolute():
        video_path = (Path(settings.DATA_DIR) / video_path).resolve()

    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_path.name
    )
