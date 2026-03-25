# backend/app/tasks/topic_tasks.py
"""Celery tasks for fetching hot topics"""
import logging
from datetime import datetime

from app.tasks.celery_app import celery_app
from app.services.hot_topic_fetcher import get_fetcher, HotTopicFetcher
from app.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.topic_tasks.fetch_all_topics_task")
def fetch_all_topics_task(self, platforms: list = None):
    """
    Fetch hot topics from all platforms and save to database

    This task is scheduled to run hourly via Celery Beat.

    Args:
        platforms: Optional list of specific platforms to fetch.
                   If None, uses TOPIC_PLATFORMS from settings.

    Returns:
        Dict with status and counts per platform
    """
    logger.info(f"Starting fetch_all_topics_task at {datetime.utcnow()}")

    try:
        fetcher = get_fetcher()
        db = SessionLocal()

        try:
            # Use async fetch in sync context
            import asyncio
            results = asyncio.run(fetch_and_save_async(fetcher, db, platforms))

            total = sum(results.values())
            logger.info(f"Completed fetch_all_topics_task: {total} topics from {len(results)} platforms")

            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "platforms": results,
                "total": total
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in fetch_all_topics_task: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, name="app.tasks.topic_tasks.fetch_platform_topics_task")
def fetch_platform_topics_task(self, platform: str):
    """
    Fetch hot topics from a single platform

    Args:
        platform: Platform identifier (e.g., 'weibo', 'douyin')

    Returns:
        Dict with status and count
    """
    logger.info(f"Fetching topics from {platform}")

    try:
        fetcher = get_fetcher()
        db = SessionLocal()

        try:
            import asyncio
            topics = asyncio.run(fetcher.fetch_platform(platform))

            if topics:
                count = fetcher.save_topics(db, topics, platform)
                return {
                    "status": "success",
                    "platform": platform,
                    "count": count
                }
            else:
                return {
                    "status": "success",
                    "platform": platform,
                    "count": 0,
                    "message": "No topics fetched"
                }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error fetching {platform}: {e}")
        return {
            "status": "error",
            "platform": platform,
            "error": str(e)
        }


@celery_app.task(name="app.tasks.topic_tasks.cleanup_old_topics_task")
def cleanup_old_topics_task(days: int = 7):
    """
    Clean up topics older than specified days

    Args:
        days: Number of days to keep (default 7)

    Returns:
        Dict with status and deleted count
    """
    from sqlalchemy import delete, and_
    from datetime import timedelta

    logger.info(f"Cleaning up topics older than {days} days")

    try:
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = db.execute(
                delete(Topic).where(Topic.fetched_at < cutoff)
            )
            db.commit()
            deleted = result.rowcount

            logger.info(f"Deleted {deleted} old topics")
            return {
                "status": "success",
                "deleted_count": deleted,
                "cutoff": cutoff.isoformat()
            }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error cleaning up old topics: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


async def fetch_and_save_async(fetcher: HotTopicFetcher, db, platforms: list = None) -> dict:
    """Async wrapper for fetch_and_save"""
    return await fetcher.fetch_and_save(db, platforms)
