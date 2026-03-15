# backend/app/tasks/celery_app.py
"""Celery Application Configuration"""
from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "video_automation",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.video_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    result_expires=3600,  # Results expire after 1 hour
)

# Optional: Configure task routes for different queues
celery_app.conf.task_routes = {
    "app.tasks.video_tasks.synthesize_video_task": {"queue": "video"},
}
