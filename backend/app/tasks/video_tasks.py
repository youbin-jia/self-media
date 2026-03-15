# backend/app/tasks/video_tasks.py
"""Celery Tasks for Video Synthesis"""
import os
from typing import Dict, Any
from celery import current_task
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.project import Project
from app.services.video_synthesizer import VideoSynthesizer


@celery_app.task(bind=True)
def synthesize_video_task(self, project_id: str) -> Dict[str, Any]:
    """
    Celery task to synthesize video from project materials

    Args:
        project_id: The project ID to synthesize video for

    Returns:
        Dictionary with task result including video path and status
    """
    db: Session = SessionLocal()

    try:
        # Update progress: Starting
        current_task.update_state(
            state="PROGRESS",
            meta={"progress": 0, "status": "Initializing video synthesis..."}
        )

        # Get project
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Update project status
        project.status = "synthesizing"
        db.commit()

        # Update progress: Loading materials
        current_task.update_state(
            state="PROGRESS",
            meta={"progress": 10, "status": "Loading materials..."}
        )

        # Initialize video synthesizer
        synthesizer = VideoSynthesizer()

        # Get materials from project metadata
        metadata = project.project_metadata or {}
        materials = metadata.get("materials", [])

        if not materials:
            raise ValueError("No materials found in project metadata")

        # Update progress: Processing
        current_task.update_state(
            state="PROGRESS",
            meta={"progress": 20, "status": "Processing materials..."}
        )

        # Synthesize video with progress callback
        def progress_callback(progress: int, status: str):
            """Update task progress"""
            current_task.update_state(
                state="PROGRESS",
                meta={"progress": progress, "status": status}
            )

        video_path = synthesizer.synthesize(
            project_id=project_id,
            materials=materials,
            progress_callback=progress_callback
        )

        # Update progress: Finalizing
        current_task.update_state(
            state="PROGRESS",
            meta={"progress": 90, "status": "Finalizing..."}
        )

        # Update project status and metadata
        project.status = "preview_ready"
        if not project.project_metadata:
            project.project_metadata = {}
        project.project_metadata["video_path"] = video_path
        db.commit()

        # Update progress: Complete
        current_task.update_state(
            state="PROGRESS",
            meta={"progress": 100, "status": "Video synthesis complete!"}
        )

        return {
            "status": "success",
            "project_id": project_id,
            "video_path": video_path,
            "message": "Video synthesis completed successfully"
        }

    except Exception as e:
        # Update project status to error
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "error"
                if not project.project_metadata:
                    project.project_metadata = {}
                project.project_metadata["error"] = str(e)
                db.commit()
        except Exception:
            pass

        # Update task state
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e), "progress": 0}
        )

        raise

    finally:
        db.close()
