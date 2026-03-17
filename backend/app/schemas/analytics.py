# backend/app/schemas/analytics.py
"""
Pydantic schemas for analytics API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class StatisticsResponse(BaseModel):
    """Schema for project statistics response."""
    total_projects: int
    status_distribution: Dict[str, int]
    success_rate: float
    average_processing_time: Optional[float] = None


class StatusDistributionResponse(BaseModel):
    """Schema for status distribution response."""
    status_distribution: Dict[str, int]


class SuccessRateResponse(BaseModel):
    """Schema for success rate response."""
    success_rate: float
    completed_projects: int = Field(..., description="Number of completed projects")
    failed_projects: int = Field(..., description="Number of failed projects")


class ProcessingTimeResponse(BaseModel):
    """Schema for average processing time response."""
    average_processing_time: Optional[float] = None
    unit: str = "seconds"


class TimelineItem(BaseModel):
    """Schema for a single timeline item."""
    date: str
    count: int


class TimelineResponse(BaseModel):
    """Schema for timeline response."""
    period: str
    timeline: List[TimelineItem]


class RecentActivityItem(BaseModel):
    """Schema for a recent activity item."""
    project_id: str
    title: str
    status: str
    updated_at: Optional[datetime] = None


class DashboardResponse(BaseModel):
    """Schema for dashboard summary response."""
    total_projects: int
    status_distribution: Dict[str, int]
    success_rate: float
    average_processing_time: Optional[float] = None
    recent_activities: List[RecentActivityItem]
    active_projects: int = Field(..., description="Number of projects currently being processed")
    completed_this_week: int = Field(..., description="Number of projects completed this week")
