# backend/app/api/topics.py
"""Topics API Router"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.topic import Topic
from app.services.hot_topic_fetcher import get_fetcher, HotTopicFetcher

router = APIRouter()


@router.get("/list")
async def list_topics(
    source: Optional[str] = Query(
        None,
        description="Filter by source platform (weibo, douyin, bilibili, zhihu, etc.)"
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of topics to return"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of topics to skip for pagination"
    ),
    db: Session = Depends(get_db)
):
    """
    List hot topics from database

    Args:
        source: Optional source filter
        limit: Maximum number of results
        offset: Pagination offset
        db: Database session

    Returns:
        List of hot topics sorted by popularity
    """
    query = db.query(Topic)

    if source:
        query = query.filter(Topic.source == source)

    # Get total count for pagination
    total = query.count()

    # Sort by hot_score descending
    topics = query.order_by(desc(Topic.hot_score)).offset(offset).limit(limit).all()

    # Get the latest fetch time
    latest = db.query(Topic).order_by(desc(Topic.fetched_at)).first()
    last_updated = latest.fetched_at.isoformat() if latest else None

    return {
        "success": True,
        "count": len(topics),
        "total": total,
        "offset": offset,
        "limit": limit,
        "last_updated": last_updated,
        "data": [topic.to_dict() for topic in topics]
    }


@router.post("/refresh")
async def refresh_topics(
    platform: Optional[str] = Query(
        None,
        description="Specific platform to refresh (optional, refreshes all if not specified)"
    ),
    db: Session = Depends(get_db)
):
    """
    Refresh topic data by fetching from DailyHotApi

    Manually trigger a refresh of topic data.

    Args:
        platform: Optional specific platform to refresh

    Returns:
        Refresh status with counts per platform
    """
    try:
        fetcher = get_fetcher()

        if platform:
            # Fetch single platform
            topics = await fetcher.fetch_platform(platform)
            count = fetcher.save_topics(db, topics, platform)
            result = {platform: count}
        else:
            # Fetch all configured platforms
            result = await fetcher.fetch_and_save(db)

        total = sum(result.values())

        return {
            "success": True,
            "status": "refreshed",
            "message": f"Refreshed {total} topics from {len(result)} platform(s)",
            "platforms": result,
            "total": total,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh topics: {str(e)}")


@router.get("/platforms")
async def list_platforms():
    """
    List supported platforms

    Returns:
        List of supported platforms with display names
    """
    platforms = HotTopicFetcher.get_supported_platforms()
    return {
        "success": True,
        "count": len(platforms),
        "data": platforms
    }


@router.get("/stats")
async def get_topic_stats(db: Session = Depends(get_db)):
    """
    Get statistics about cached topics

    Returns:
        Statistics including counts per platform and last update time
    """
    from sqlalchemy import func

    # Get count per platform
    platform_counts = db.query(
        Topic.source,
        func.count(Topic.id).label('count'),
        func.max(Topic.fetched_at).label('last_fetch')
    ).group_by(Topic.source).all()

    # Get total count
    total = db.query(Topic).count()

    # Get latest fetch time
    latest = db.query(Topic).order_by(desc(Topic.fetched_at)).first()
    last_updated = latest.fetched_at.isoformat() if latest else None

    platforms = [
        {
            "source": row.source,
            "count": row.count,
            "last_fetch": row.last_fetch.isoformat() if row.last_fetch else None
        }
        for row in platform_counts
    ]

    return {
        "success": True,
        "total_topics": total,
        "last_updated": last_updated,
        "platforms": platforms
    }


@router.delete("/cleanup")
async def cleanup_old_topics(
    days: int = Query(
        7,
        ge=1,
        le=30,
        description="Delete topics older than this many days"
    ),
    db: Session = Depends(get_db)
):
    """
    Clean up old cached topics

    Args:
        days: Number of days to keep (delete older)

    Returns:
        Number of deleted topics
    """
    from sqlalchemy import delete
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    result = db.execute(
        delete(Topic).where(Topic.fetched_at < cutoff)
    )
    db.commit()

    return {
        "success": True,
        "deleted_count": result.rowcount,
        "cutoff": cutoff.isoformat()
    }
