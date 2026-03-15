# backend/app/api/topics.py
"""Topics API Router"""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.topic_monitor import TopicMonitor

router = APIRouter()

# Create singleton instance
topic_monitor = TopicMonitor()


@router.get("/list")
async def list_topics(
    source: Optional[str] = Query(
        None,
        description="Filter by source platform (weibo, douyin, toutiao, bilibili)"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of topics to return"
    )
):
    """
    List hot topics from monitored platforms

    Args:
        source: Optional source filter
        limit: Maximum number of results

    Returns:
        List of hot topics sorted by popularity
    """
    topics = await topic_monitor.fetch_topics(source=source, limit=limit)
    return {
        "success": True,
        "count": len(topics),
        "data": topics
    }


@router.post("/refresh")
async def refresh_topics():
    """
    Refresh topic data

    Manually trigger a refresh of topic data (mock implementation
    randomly adjusts hot scores)

    Returns:
        Refresh status
    """
    result = await topic_monitor.refresh_topics()
    return {
        "success": True,
        **result
    }
