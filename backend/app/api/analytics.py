# backend/app/api/analytics.py
"""
Analytics API Endpoints.

Provides REST API for analytics and dashboard functionality:
- Project statistics
- Status distribution
- Success rate
- Processing time
- Timeline data
- Dashboard summary
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics.collector import MetricsCollector
from app.services.analytics.dashboard import DashboardService
from app.schemas.analytics import (
    StatisticsResponse,
    StatusDistributionResponse,
    SuccessRateResponse,
    ProcessingTimeResponse,
    TimelineResponse,
    DashboardResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get comprehensive project statistics.

    Returns aggregated statistics including total count,
    status distribution, success rate, and average processing time.

    Args:
        db: Database session

    Returns:
        Project statistics
    """
    collector = MetricsCollector(db=db)
    stats = collector.get_project_statistics()

    return StatisticsResponse(**stats)


@router.get("/status-distribution", response_model=StatusDistributionResponse)
async def get_status_distribution(db: Session = Depends(get_db)):
    """
    Get distribution of projects by status.

    Returns a dictionary mapping each status to the count
    of projects with that status.

    Args:
        db: Database session

    Returns:
        Status distribution data
    """
    collector = MetricsCollector(db=db)
    distribution = collector.get_status_distribution()

    return StatusDistributionResponse(status_distribution=distribution)


@router.get("/success-rate", response_model=SuccessRateResponse)
async def get_success_rate(db: Session = Depends(get_db)):
    """
    Get success rate of completed projects.

    Calculates the success rate based only on projects
    with 'completed' or 'failed' status. Pending or
    processing projects are excluded.

    Args:
        db: Database session

    Returns:
        Success rate data with counts
    """
    collector = MetricsCollector(db=db)

    # Get success rate
    success_rate = collector.get_success_rate()

    # Get counts for context
    from sqlalchemy import func
    from app.models.project import Project

    completed = (
        db.query(func.count(Project.id))
        .filter(Project.status == "completed")
        .scalar() or 0
    )

    failed = (
        db.query(func.count(Project.id))
        .filter(Project.status == "failed")
        .scalar() or 0
    )

    return SuccessRateResponse(
        success_rate=success_rate,
        completed_projects=completed,
        failed_projects=failed,
    )


@router.get("/processing-time", response_model=ProcessingTimeResponse)
async def get_processing_time(db: Session = Depends(get_db)):
    """
    Get average processing time for completed projects.

    Processing time is calculated as (updated_at - created_at)
    for projects with 'completed' status.

    Args:
        db: Database session

    Returns:
        Average processing time in seconds
    """
    collector = MetricsCollector(db=db)
    avg_time = collector.get_average_processing_time()

    return ProcessingTimeResponse(
        average_processing_time=avg_time,
        unit="seconds",
    )


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    period: str = Query(
        "daily",
        description="Time period: daily, weekly, or monthly"
    ),
    days: Optional[int] = Query(
        None,
        ge=1,
        le=365,
        description="Number of days for daily period"
    ),
    weeks: Optional[int] = Query(
        None,
        ge=1,
        le=52,
        description="Number of weeks for weekly period"
    ),
    months: Optional[int] = Query(
        None,
        ge=1,
        le=24,
        description="Number of months for monthly period"
    ),
    db: Session = Depends(get_db)
):
    """
    Get timeline of projects created over time.

    Returns a chronological list of time periods with
    project counts for each period.

    Args:
        period: Time period - "daily", "weekly", or "monthly"
        days: Number of days for daily period (default: 7)
        weeks: Number of weeks for weekly period (default: 4)
        months: Number of months for monthly period (default: 6)
        db: Database session

    Returns:
        Timeline data with date and count for each period
    """
    collector = MetricsCollector(db=db)

    timeline = collector.get_projects_timeline(
        period=period,
        days=days,
        weeks=weeks,
        months=months,
    )

    return TimelineResponse(
        period=period,
        timeline=timeline,
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Get dashboard summary.

    Provides a comprehensive summary for dashboard views
    including statistics, recent activities, and key metrics.

    Args:
        db: Database session

    Returns:
        Dashboard summary data
    """
    dashboard_service = DashboardService(db=db)
    summary = dashboard_service.get_dashboard_summary()

    return DashboardResponse(**summary)
