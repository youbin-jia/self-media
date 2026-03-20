# backend/app/tasks/video_tasks.py
"""Celery Tasks for Video Synthesis"""
import os
import logging
from typing import Dict, Any, List
from celery import current_task
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.project import Project
from app.services.video_synthesizer import VideoSynthesizer

logger = logging.getLogger(__name__)

# Task priority constants
VIDEO_SYNTHESIS_PRIORITY = 9  # Highest priority - video synthesis


@celery_app.task(bind=True)
def synthesize_video_task(
    self,
    project_id: str,
    platforms: List[str] = None
) -> Dict[str, Any]:
    """
    Celery task to synthesize video from project materials (supports multi-platform)

    Args:
        project_id: The project ID to synthesize video for
        platforms: List of platforms to export for (e.g., ["horizontal", "vertical", "square"])

    Returns:
        Dictionary with task result including video path and status
    """
    if platforms is None:
        platforms = ["horizontal"]

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

        # Create base video clip from materials
        base_clip = synthesizer.synthesize(
            project_id=project_id,
            materials=materials,
            progress_callback=progress_callback
        )

        # Export for each platform
        outputs = {}
        for i, platform in enumerate(platforms):
            progress = 20 + int((i / len(platforms)) * 70)
            current_task.update_state(
                state="PROGRESS",
                meta={"progress": progress, "status": f"Exporting for {platform}..."}
            )

            output_path = synthesizer.get_output_path(project_id, platform)
            # Load the base clip
            from moviepy import  VideoFileClip
            clip = VideoFileClip(base_clip)
            try:
                synthesizer.export_for_platform(clip, platform, output_path)
                outputs[platform] = output_path
            finally:
                clip.close()

        # Update progress: Finalizing
        current_task.update_state(
            state="PROGRESS",
            meta={"progress": 90, "status": "Finalizing..."}
        )

        # Update project status and metadata
        project.status = "preview_ready"
        if not project.project_metadata:
            project.project_metadata = {}
        project.project_metadata["video_path"] = outputs.get("horizontal") or outputs.get(platforms[0])
        project.project_metadata["video_paths"] = outputs
        db.commit()

        # Update progress: Complete
        current_task.update_state(
            state="PROGRESS",
            meta={"progress": 100, "status": "Video synthesis complete!"}
        )

        return {
            "status": "success",
            "project_id": project_id,
            "outputs": outputs,
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
        except Exception as inner_e:
            logger.error(f"Failed to update project error status: {inner_e}")

        # Update task state
        current_task.update_state(
            state="FAILURE",
            meta={"error": str(e), "progress": 0}
        )

        raise

    finally:
        db.close()
