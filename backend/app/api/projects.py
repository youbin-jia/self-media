# backend/app/api/projects.py
"""Project API Routes"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import time
import asyncio

from app.database import get_db
from app.models.project import Project
from app.models.script import Script
from app.models.script_history import ScriptHistory
from app.schemas.script import ScriptSegment
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.script_generator import ScriptGenerator
from app.services.quality_detector import get_quality_detector

router = APIRouter()
WORKFLOW_STEPS = ["script", "review", "visual", "audio", "video"]
OUTLINE_LLM_TIMEOUT_SEC = 90
FULL_SCRIPT_LLM_TIMEOUT_SEC = 150


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
    llm_call: Optional[dict] = None
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

    steps = metadata.get("steps", {})
    step = steps.get(step_name, {})
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
    step["progress"] = progress

    steps[step_name] = step
    metadata["steps"] = steps
    project.current_step = step_name
    project.project_metadata = metadata
    db.commit()


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
            report = detector.detect_script_quality(script.full_script or "", review_segments)

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
            output=output
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
                }
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
