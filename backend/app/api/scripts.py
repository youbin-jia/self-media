# backend/app/api/scripts.py
"""Script API Routes"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.script import Script
from app.models.script_history import ScriptHistory
from app.models.project import Project
from app.schemas.script import ScriptCreate, ScriptUpdate, ScriptResponse, ScriptSegment
from app.services.script_generator import ScriptGenerator

router = APIRouter()


class ScriptAIReviseRequest(BaseModel):
    issues: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None
    extra_instruction: Optional[str] = None


def _create_script_snapshot(db: Session, script: Script, source: str):
    """Persist a script snapshot for history and rollback."""
    _ensure_script_history_table(db)
    snapshot = ScriptHistory(
        script_id=script.id,
        project_id=script.project_id,
        version=script.version or 1,
        outline=script.outline,
        full_script=script.full_script,
        segments=script.segments,
        source=source
    )
    db.add(snapshot)
    db.flush()
    _prune_script_history(db, script.project_id, keep=10)


def _ensure_script_history_table(db: Session):
    """Ensure script history table exists for old databases without migration."""
    bind = db.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(ScriptHistory.__tablename__):
        ScriptHistory.__table__.create(bind=bind, checkfirst=True)


def _prune_script_history(db: Session, project_id: str, keep: int = 10):
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


@router.post("/generate-outline", response_model=dict)
async def generate_outline(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a script outline for a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        Dictionary with outline text
    """
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate outline
    generator = ScriptGenerator()
    topic = project.topic_title or project.title
    outline = await generator.generate_outline(topic)

    # Create or update script
    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script:
        script = Script(
            project_id=project_id,
            outline=outline,
            version=1,
            is_approved=False
        )
        db.add(script)
    else:
        script.outline = outline
        script.version = (script.version or 1) + 1

    db.commit()
    db.refresh(script)

    return {
        "script_id": script.id,
        "outline": outline
    }


@router.post("/generate-full", response_model=ScriptResponse)
async def generate_full_script(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a full script with segments for a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        ScriptResponse with full script and segments
    """
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get existing script with outline
    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script or not script.outline:
        raise HTTPException(
            status_code=400,
            detail="No outline found. Please generate outline first."
        )

    # Generate full script
    generator = ScriptGenerator()
    topic = project.topic_title or project.title
    result = await generator.generate_full_script(script.outline, topic)

    # Update script
    script.full_script = result["full_script"]
    script.segments = [seg.model_dump() for seg in result["segments"]]
    script.version = (script.version or 1) + 1

    db.commit()
    db.refresh(script)

    return script


@router.post("/{script_id}/approve", response_model=ScriptResponse)
async def approve_script(
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Approve a script

    Args:
        script_id: The script ID
        db: Database session

    Returns:
        Updated ScriptResponse
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    script.is_approved = True
    db.commit()
    db.refresh(script)

    return script


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a script by ID

    Args:
        script_id: The script ID
        db: Database session

    Returns:
        ScriptResponse
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return script


@router.get("/project/{project_id}", response_model=ScriptResponse)
async def get_project_script(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the script for a project

    Args:
        project_id: The project ID
        db: Database session

    Returns:
        ScriptResponse
    """
    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return script


@router.put("/project/{project_id}", response_model=ScriptResponse)
async def update_project_script(
    project_id: str,
    script_in: ScriptUpdate,
    db: Session = Depends(get_db)
):
    """
    Update script content by project ID.

    This endpoint is mainly used for manual editing in workflow UI.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script:
        script = Script(
            project_id=project_id,
            version=1,
            is_approved=False
        )
        db.add(script)

    if script_in.outline is not None:
        script.outline = script_in.outline
    if script_in.full_script is not None:
        script.full_script = script_in.full_script
    if script_in.segments is not None:
        script.segments = [seg.model_dump() for seg in script_in.segments]
    if script_in.is_approved is not None:
        script.is_approved = script_in.is_approved

    script.version = (script.version or 1) + 1
    _create_script_snapshot(db, script, source="manual_edit")

    # Keep workflow output in sync so /api/projects/{id} reflects latest edit.
    metadata = dict(project.project_metadata or {})
    steps = metadata.get("steps")
    if isinstance(steps, dict) and isinstance(steps.get("script"), dict):
        if script_in.full_script is not None:
            steps["script"].setdefault("output", {})
            steps["script"]["output"]["full_script"] = script_in.full_script
        if script_in.outline is not None:
            steps["script"].setdefault("output", {})
            steps["script"]["output"]["outline"] = script_in.outline
        metadata["steps"] = steps
        project.project_metadata = metadata

    db.commit()
    db.refresh(script)
    return script


@router.get("/project/{project_id}/history")
async def get_project_script_history(
    project_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get script edit history for a project."""
    _ensure_script_history_table(db)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    history = (
        db.query(ScriptHistory)
        .filter(ScriptHistory.project_id == project_id)
        .order_by(ScriptHistory.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": h.id,
            "version": h.version,
            "source": h.source,
            "created_at": h.created_at,
            "outline": h.outline,
            "full_script": h.full_script
        }
        for h in history
    ]


@router.delete("/project/{project_id}/history/{history_id}")
async def delete_project_script_history(
    project_id: str,
    history_id: str,
    confirm: bool = Query(False, description="Must be true to confirm destructive delete"),
    db: Session = Depends(get_db)
):
    """Delete one history snapshot by ID."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Deletion requires confirm=true")
    _ensure_script_history_table(db)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    history = (
        db.query(ScriptHistory)
        .filter(
            ScriptHistory.id == history_id,
            ScriptHistory.project_id == project_id
        )
        .first()
    )
    if not history:
        raise HTTPException(status_code=404, detail="History record not found")

    db.delete(history)
    db.commit()
    return {"success": True, "deleted_id": history_id}


@router.delete("/project/{project_id}/history")
async def clear_project_script_history(
    project_id: str,
    confirm: bool = Query(False, description="Must be true to confirm destructive cleanup"),
    db: Session = Depends(get_db)
):
    """Delete all history snapshots for a project."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Cleanup requires confirm=true")
    _ensure_script_history_table(db)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    deleted_count = (
        db.query(ScriptHistory)
        .filter(ScriptHistory.project_id == project_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"success": True, "deleted_count": deleted_count}


@router.post("/project/{project_id}/rollback/{history_id}", response_model=ScriptResponse)
async def rollback_project_script(
    project_id: str,
    history_id: str,
    db: Session = Depends(get_db)
):
    """Rollback script to a selected history snapshot."""
    _ensure_script_history_table(db)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    history = (
        db.query(ScriptHistory)
        .filter(
            ScriptHistory.id == history_id,
            ScriptHistory.project_id == project_id
        )
        .first()
    )
    if not history:
        raise HTTPException(status_code=404, detail="History record not found")

    script.outline = history.outline
    script.full_script = history.full_script
    script.segments = history.segments
    script.version = (script.version or 1) + 1
    _create_script_snapshot(db, script, source=f"rollback_to_v{history.version}")

    metadata = dict(project.project_metadata or {})
    steps = metadata.get("steps")
    if isinstance(steps, dict) and isinstance(steps.get("script"), dict):
        steps["script"].setdefault("output", {})
        steps["script"]["output"]["outline"] = script.outline
        steps["script"]["output"]["full_script"] = script.full_script
        steps["script"]["output"]["segments_count"] = len(script.segments or [])
        metadata["steps"] = steps
        project.project_metadata = metadata

    db.commit()
    db.refresh(script)
    return script


@router.post("/project/{project_id}/ai-revise")
async def ai_revise_project_script(
    project_id: str,
    request: ScriptAIReviseRequest,
    db: Session = Depends(get_db)
):
    """Generate an AI revision candidate from review feedback without auto-saving."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    script = db.query(Script).filter(Script.project_id == project_id).first()
    if not script or not (script.full_script or "").strip():
        raise HTTPException(status_code=400, detail="No script found for revision")

    issues = request.issues or []
    recommendations = request.recommendations or []
    if not issues and not recommendations:
        raise HTTPException(status_code=400, detail="No review feedback provided")

    issue_lines = []
    for idx, item in enumerate(issues, start=1):
        issue_lines.append(
            f"{idx}. 类型：{item.get('type') or '未分类'}；严重级别：{item.get('severity') or 'medium'}；描述：{item.get('message') or ''}"
        )
    if not issue_lines:
        issue_lines = ["（无明确问题条目）"]

    rec_lines = [f"{idx}. {rec}" for idx, rec in enumerate(recommendations, start=1)] or ["（无明确建议条目）"]
    extra_instruction = (request.extra_instruction or "").strip()

    prompt = f"""你是一位资深中文短视频脚本总编。请根据审核意见对“完整脚本”进行修订。

要求：
1. 直接输出“修订后的完整脚本正文”，不要输出解释
2. 必须中文输出，术语可保留英文
3. 优先修复高严重级别问题
4. 保持主题与核心信息，不要删减关键信息
5. 保持可执行性（分镜、旁白、节奏、音乐提示尽量完整）

项目主题：{project.topic_title or project.title}

审核问题：
{chr(10).join(issue_lines)}

审核建议：
{chr(10).join(rec_lines)}

补充要求：
{extra_instruction or '无'}

当前完整脚本：
{script.full_script}
"""

    generator = ScriptGenerator()
    try:
        revised_full_script = await generator.llm.generate(prompt, max_tokens=4096, temperature=0.35)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI revise failed: {str(exc)}")

    return {
        "project_id": project_id,
        "script_id": script.id,
        "script_version": script.version or 1,
        "generated_at": datetime.now().isoformat(),
        "original_full_script": script.full_script,
        "revised_full_script": revised_full_script,
        "llm_input": {
            "provider": generator.provider_name,
            "prompt": prompt
        }
    }
