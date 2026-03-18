# backend/app/tasks/batch_tasks.py
"""
Celery tasks for batch video processing.

Handles batch job execution with Redis state management
and proper error handling.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List
from celery import current_task

from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models.batch import BatchPriority, BatchStatus
from app.models.project import Project
from app.services.batch_state import get_batch_state_manager
from app.tasks.video_tasks import synthesize_video_task

logger = logging.getLogger(__name__)

# Task priority constants
BATCH_PROCESSING_PRIORITY = 8  # High priority - batch processing
BATCH_MONITOR_PRIORITY = 4     # Medium priority - monitoring


@celery_app.task(bind=True)
def process_batch_task(self, batch_id: str) -> Dict[str, Any]:
    """
    Process a batch of video generation tasks.

    This task orchestrates the processing of multiple projects in a batch,
    managing concurrency and tracking progress via Redis.

    Args:
        batch_id: Unique batch identifier

    Returns:
        Dictionary with batch processing results

    Raises:
        ValueError: If batch not found or invalid
        Exception: For processing errors
    """
    db = SessionLocal()
    state_manager = get_batch_state_manager()

    try:
        logger.info(f"Starting batch processing for batch {batch_id}")

        # Get batch data from Redis
        batch_data = state_manager.get_batch(batch_id)
        if not batch_data:
            raise ValueError(f"Batch {batch_id} not found")

        project_ids = batch_data.get("project_ids", [])
        priority_str = batch_data.get("priority", "normal")
        concurrency = int(batch_data.get("concurrency", 3))
        total_projects = int(batch_data.get("total_projects", 0))

        # Update status to running
        state_manager.update_status(
            batch_id=batch_id,
            status=BatchStatus.RUNNING,
            started_at=datetime.utcnow().isoformat()
        )

        logger.info(
            f"Processing batch {batch_id}: {len(project_ids)} projects, "
            f"priority={priority_str}, concurrency={concurrency}"
        )

        # Get Celery priority
        celery_priority = BatchPriority.to_celery_priority(priority_str)

        # Process each project
        spawned_tasks = []
        for project_id in project_ids:
            try:
                # Get project from database
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    logger.warning(f"Project {project_id} not found, skipping")
                    state_manager.add_error(
                        batch_id=batch_id,
                        project_id=project_id,
                        error_message="Project not found"
                    )
                    state_manager.increment_failed(batch_id)
                    continue

                # Spawn video synthesis task
                task = synthesize_video_task.delay(
                    project_id=project_id,
                    priority=celery_priority
                )

                # Record task ID
                state_manager.add_task_id(batch_id, task.id)
                spawned_tasks.append(task.id)

                logger.info(
                    f"Spawned video task {task.id} for project {project_id}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to spawn task for project {project_id}: {e}"
                )
                state_manager.add_error(
                    batch_id=batch_id,
                    project_id=project_id,
                    error_message=str(e)
                )
                state_manager.increment_failed(batch_id)

        # Update final status
        state_manager.update_status(
            batch_id=batch_id,
            status=BatchStatus.COMPLETED,
            completed_at=datetime.utcnow().isoformat()
        )

        logger.info(
            f"Batch {batch_id} processing completed: "
            f"{len(spawned_tasks)} tasks spawned"
        )

        return {
            "status": "success",
            "batch_id": batch_id,
            "tasks_spawned": len(spawned_tasks),
            "task_ids": spawned_tasks,
        }

    except Exception as e:
        logger.error(f"Batch {batch_id} processing failed: {e}", exc_info=True)

        # Update status to failed
        try:
            state_manager.update_status(
                batch_id=batch_id,
                status=BatchStatus.FAILED,
                completed_at=datetime.utcnow().isoformat()
            )
        except Exception as update_error:
            logger.error(
                f"Failed to update batch status to failed: {update_error}"
            )

        # Record error
        try:
            state_manager.add_error(
                batch_id=batch_id,
                project_id="batch",
                error_message=str(e)
            )
        except Exception as error_error:
            logger.error(f"Failed to record error: {error_error}")

        raise

    finally:
        db.close()


@celery_app.task(bind=True)
def monitor_batch_progress_task(self, batch_id: str) -> Dict[str, Any]:
    """
    Monitor progress of a batch and update completion counts.

    This is an optional utility task that can be scheduled to check
    the status of spawned video tasks and update batch progress.

    Args:
        batch_id: Unique batch identifier

    Returns:
        Dictionary with monitoring results
    """
    from celery.result import AsyncResult

    state_manager = get_batch_state_manager()

    try:
        # Get batch data
        batch_data = state_manager.get_batch(batch_id)
        if not batch_data:
            raise ValueError(f"Batch {batch_id} not found")

        task_ids = state_manager.get_task_ids(batch_id)

        completed = 0
        failed = 0

        # Check each task status
        for task_id in task_ids:
            result = AsyncResult(task_id)
            if result.successful():
                completed += 1
            elif result.failed():
                failed += 1

        # Note: We don't update Redis counts here as the video tasks
        # themselves should update counts upon completion

        logger.info(
            f"Batch {batch_id} progress: {completed} completed, {failed} failed"
        )

        return {
            "batch_id": batch_id,
            "completed": completed,
            "failed": failed,
            "total": len(task_ids),
        }

    except Exception as e:
        logger.error(f"Failed to monitor batch {batch_id}: {e}")
        raise
