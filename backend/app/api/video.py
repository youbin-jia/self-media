# backend/app/api/video.py
"""Video API Routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from app.database import get_db
from app.models.project import Project
from app.tasks.video_tasks import synthesize_video_task

router = APIRouter()


class SynthesizeRequest(BaseModel):
    """Request model for video synthesis"""
    project_id: str


class SynthesizeResponse(BaseModel):
    """Response model for video synthesis"""
    task_id: str
    project_id: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    task_id: str
    status: str
    progress: int
    message: str
    result: Dict[str, Any] = {}


@router.post("/synthesize", response_model=SynthesizeResponse, status_code=202)
async def trigger_synthesis(
    request: SynthesizeRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger video synthesis for a project

    Args:
        request: Synthesis request with project_id
        db: Database session

    Returns:
        Task ID and project ID for tracking

    Raises:
        HTTPException: 404 if project not found, 400 if project not ready
    """
    # Check if project exists
    project = db.query(Project).filter(Project.id == request.project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if project has materials
    metadata = project.project_metadata or {}
    materials = metadata.get("materials", [])

    if not materials:
        raise HTTPException(
            status_code=400,
            detail="Project has no materials. Please collect materials first."
        )

    # Trigger Celery task
    task = synthesize_video_task.delay(request.project_id)

    return SynthesizeResponse(
        task_id=task.id,
        project_id=request.project_id,
        message="Video synthesis task started"
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a video synthesis task

    Args:
        task_id: The Celery task ID

    Returns:
        Task status with progress information
    """
    from app.tasks.celery_app import celery_app

    # Get task result
    task_result = celery_app.AsyncResult(task_id)

    # Prepare response
    response = TaskStatusResponse(
        task_id=task_id,
        status=task_result.status,
        progress=0,
        message="",
        result={}
    )

    if task_result.status == "PENDING":
        response.message = "Task is waiting to start"
        response.progress = 0

    elif task_result.status == "PROGRESS":
        # Get progress info from task state
        info = task_result.info or {}
        response.progress = info.get("progress", 0)
        response.message = info.get("status", "In progress...")

    elif task_result.status == "SUCCESS":
        response.progress = 100
        response.message = "Task completed successfully"
        response.result = task_result.result or {}

    elif task_result.status == "FAILURE":
        response.message = "Task failed"
        response.result = {
            "error": str(task_result.info) if task_result.info else "Unknown error"
        }

    else:
        response.message = f"Task status: {task_result.status}"

    return response
