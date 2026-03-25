# backend/app/tasks/celery_app.py
"""Celery Application Configuration"""
from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

from app.config import settings

# Create Celery app
celery_app = Celery(
    "video_automation",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.video_tasks", "app.tasks.batch_tasks", "app.tasks.topic_tasks"]
)

# Define task queues with priorities
# high: Video synthesis, batch processing (priority 8-9)
# medium: Material collection, webhooks (priority 4-5)
# low: Cleanup tasks (priority 1)
task_queues = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('medium', Exchange('medium'), routing_key='medium'),
    Queue('low', Exchange('low'), routing_key='low'),
)

# Task routing configuration with priorities
task_routes = {
    # High priority queue - Video synthesis, batch processing
    'app.tasks.video_tasks.synthesize_video_task': {
        'queue': 'high',
        'priority': 9,
    },
    'app.tasks.batch_tasks.process_batch_task': {
        'queue': 'high',
        'priority': 8,
    },
    # Medium priority queue - Material collection, webhooks, monitoring, topics
    'app.tasks.batch_tasks.monitor_batch_progress_task': {
        'queue': 'medium',
        'priority': 4,
    },
    'app.tasks.topic_tasks.fetch_all_topics_task': {
        'queue': 'medium',
        'priority': 5,
    },
    'app.tasks.topic_tasks.fetch_platform_topics_task': {
        'queue': 'medium',
        'priority': 5,
    },
    # Low priority queue - Cleanup tasks
    'app.tasks.topic_tasks.cleanup_old_topics_task': {
        'queue': 'low',
        'priority': 1,
    },
}

# Celery Beat schedule for periodic tasks
beat_schedule = {
    # Fetch hot topics every hour
    'fetch-topics-hourly': {
        'task': 'app.tasks.topic_tasks.fetch_all_topics_task',
        'schedule': crontab(minute=0),  # Run at the start of every hour
        'options': {'queue': 'medium'},
    },
    # Cleanup old topics daily at 3 AM
    'cleanup-topics-daily': {
        'task': 'app.tasks.topic_tasks.cleanup_old_topics_task',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {'days': 7},
        'options': {'queue': 'low'},
    },
}

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    result_expires=settings.CELERY_TASK_RESULT_CACHE_TTL,

    # Worker configuration
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,

    # Task reliability settings
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    task_reject_on_worker_lost=settings.CELERY_TASK_REJECT_ON_WORKER_LOST,

    # Queue configuration
    task_queues=task_queues,
    task_default_queue='medium',
    task_default_exchange='medium',
    task_default_routing_key='medium',

    # Task routing
    task_routes=task_routes,

    # Beat schedule for periodic tasks
    beat_schedule=beat_schedule,
)
