# backend/app/api/batch.py
"""
Batch Processing API Endpoints.

Provides REST API for managing batch video generation jobs:
- Create batch jobs
- Monitor progress
- Cancel jobs
- List active batches
"""
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from app.database import get_db
from app.models.batch import BatchJob, BatchStatus, BatchPriority
from app.models.project import Project
from app.schemas.batch import (
    BatchCreate,
    BatchResponse,
    BatchProgressResponse,
    BatchListResponse,
    BatchCancelResponse,
)
from app.services.batch_state import get_batch_state_manager
from app.tasks.batch_tasks import process_batch_task

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create", response_model=BatchResponse, status_code=201)
async def create_batch(
    batch_in: BatchCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new batch job.

    Creates a batch job that processes multiple video projects in parallel.

    Args:
        batch_in: Batch creation data
        db: Database session

    Returns:
        Created batch job data

    Raises:
        HTTPException: 400 if validation fails
    """
    try:
        # Validate that all projects exist
        project_ids = batch_in.project_ids
        existing_projects = (
            db.query(Project)
            .filter(Project.id.in_(project_ids))
            .all()
        )

        if len(existing_projects) != len(project_ids):
            found_ids = {p.id for p in existing_projects}
            missing = set(project_ids) - found_ids
            raise HTTPException(
                status_code=400,
                detail=f"Projects not found: {', '.join(missing)}"
            )

        # Create BatchJob in database
        batch_job = BatchJob(
            name=batch_in.name,
            project_ids=project_ids,
            total_projects=len(project_ids),
            status=BatchStatus.QUEUED,
            priority=batch_in.priority,
            concurrency=batch_in.concurrency,
        )

        db.add(batch_job)
        db.commit()
        db.refresh(batch_job)

        logger.info(f"Created batch job {batch_job.id} with {len(project_ids)} projects")

        # Create batch in Redis
        state_manager = get_batch_state_manager()
        state_manager.create_batch(
            batch_id=batch_job.id,
            project_ids=project_ids,
            concurrency=batch_in.concurrency,
            priority=batch_in.priority,
            name=batch_in.name,
        )

        # Spawn Celery task
        celery_priority = BatchPriority.to_celery_priority(batch_in.priority)
        task = process_batch_task.delay(
            batch_id=batch_job.id,
            priority=celery_priority
        )

        logger.info(f"Spawned batch task {task.id} for batch {batch_job.id}")

        # Return response
        return BatchResponse(
            batch_id=batch_job.id,
            name=batch_job.name,
            status=batch_job.status,
            priority=batch_job.priority,
            concurrency=batch_job.concurrency,
            total_projects=batch_job.total_projects,
            completed_projects=batch_job.completed_projects,
            failed_projects=batch_job.failed_projects,
            progress=f"{batch_job.progress_percentage}%",
            success_rate=f"{batch_job.success_rate}%",
            created_at=batch_job.created_at,
            started_at=batch_job.started_at,
            completed_at=batch_job.completed_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create batch: {str(e)}")


@router.get("/status/{batch_id}", response_model=BatchResponse)
async def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """
    Get batch job status.

    Retrieves the current status of a batch job from both
    database and Redis for real-time information.

    Args:
        batch_id: Batch job ID
        db: Database session

    Returns:
        Batch job data

    Raises:
        HTTPException: 404 if batch not found
    """
    # Get from database
    batch_job = db.query(BatchJob).filter(BatchJob.id == batch_id).first()

    if not batch_job:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Get real-time data from Redis
    state_manager = get_batch_state_manager()
    redis_data = state_manager.get_batch(batch_id)

    # Merge data (Redis has more up-to-date counts)
    if redis_data:
        completed_projects = int(redis_data.get("completed_projects", batch_job.completed_projects))
        failed_projects = int(redis_data.get("failed_projects", batch_job.failed_projects))
    else:
        completed_projects = batch_job.completed_projects
        failed_projects = batch_job.failed_projects

    return BatchResponse(
        batch_id=batch_job.id,
        name=batch_job.name,
        status=batch_job.status,
        priority=batch_job.priority,
        concurrency=batch_job.concurrency,
        total_projects=batch_job.total_projects,
        completed_projects=completed_projects,
        failed_projects=failed_projects,
        progress=f"{batch_job.progress_percentage}%",
        success_rate=f"{batch_job.success_rate}%",
        created_at=batch_job.created_at,
        started_at=batch_job.started_at,
        completed_at=batch_job.completed_at,
    )


@router.get("/{batch_id}/progress", response_model=BatchProgressResponse)
async def get_batch_progress(batch_id: str):
    """
    Get real-time batch progress.

    Retrieves detailed progress information from Redis
    for real-time monitoring.

    Args:
        batch_id: Batch job ID

    Returns:
        Detailed progress data

    Raises:
        HTTPException: 404 if batch not found
    """
    state_manager = get_batch_state_manager()

    progress = state_manager.get_progress(batch_id)

    if "error" in progress:
        raise HTTPException(status_code=404, detail=progress["error"])

    return BatchProgressResponse(**progress)


@router.post("/cancel/{batch_id}", response_model=BatchCancelResponse)
async def cancel_batch(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """
    Cancel a batch job.

    Cancels all pending tasks in the batch and updates status.

    Args:
        batch_id: Batch job ID
        db: Database session

    Returns:
        Cancellation confirmation

    Raises:
        HTTPException: 404 if batch not found
        HTTPException: 400 if batch already finished
    """
    # Get batch from database
    batch_job = db.query(BatchJob).filter(BatchJob.id == batch_id).first()

    if not batch_job:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Check if batch can be cancelled
    if batch_job.is_finished:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel batch with status: {batch_job.status}"
        )

    # Get task IDs from Redis
    state_manager = get_batch_state_manager()
    task_ids = state_manager.get_task_ids(batch_id)

    # Revoke all Celery tasks
    tasks_cancelled = 0
    for task_id in task_ids:
        try:
            result = AsyncResult(task_id)
            result.revoke(terminate=True)
            tasks_cancelled += 1
        except Exception as e:
            logger.warning(f"Failed to revoke task {task_id}: {e}")

    # Update status
    batch_job.status = BatchStatus.CANCELLED
    batch_job.completed_at = datetime.utcnow()
    db.commit()

    state_manager.update_status(
        batch_id=batch_id,
        status=BatchStatus.CANCELLED,
        completed_at=datetime.utcnow().isoformat()
    )

    logger.info(f"Cancelled batch {batch_id}: {tasks_cancelled} tasks revoked")

    return BatchCancelResponse(
        batch_id=batch_id,
        status=BatchStatus.CANCELLED,
        message="Batch cancelled successfully",
        tasks_cancelled=tasks_cancelled,
    )


@router.get("/list", response_model=BatchListResponse)
async def list_batches(
    status: str = Query(
        None,
        description="Filter by status (queued, running, completed, failed, cancelled)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of batches"),
    db: Session = Depends(get_db)
):
    """
    List batch jobs.

    Lists batch jobs with optional status filtering.
    Active batches (queued, running) are shown first.

    Args:
        status: Optional status filter
        limit: Maximum number of results
        db: Database session

    Returns:
        List of batch jobs
    """
    query = db.query(BatchJob)

    if status:
        query = query.filter(BatchJob.status == status)

    # Order by created_at desc
    query = query.order_by(BatchJob.created_at.desc())
    batch_jobs = query.limit(limit).all()

    # Convert to response models
    batches = [
        BatchResponse(
            batch_id=bj.id,
            name=bj.name,
            status=bj.status,
            priority=bj.priority,
            concurrency=bj.concurrency,
            total_projects=bj.total_projects,
            completed_projects=bj.completed_projects,
            failed_projects=bj.failed_projects,
            progress=f"{bj.progress_percentage}%",
            success_rate=f"{bj.success_rate}%",
            created_at=bj.created_at,
            started_at=bj.started_at,
            completed_at=bj.completed_at,
        )
        for bj in batch_jobs
    ]

    return BatchListResponse(
        batches=batches,
        total=len(batches),
    )
