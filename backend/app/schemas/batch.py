# backend/app/schemas/batch.py
"""
Pydantic schemas for batch processing API endpoints.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class BatchCreate(BaseModel):
    """Schema for creating a batch job."""
    project_ids: List[str] = Field(..., min_length=1, description="List of project IDs to process")
    name: Optional[str] = Field(None, max_length=255, description="Optional batch name")
    priority: str = Field("normal", description="Batch priority: high, normal, or low")
    concurrency: int = Field(3, ge=1, le=10, description="Number of parallel tasks")

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        """Validate priority value."""
        from app.models.batch import BatchPriority
        if not BatchPriority.is_valid(v):
            raise ValueError(f"Invalid priority. Must be one of: {BatchPriority.all()}")
        return v


class BatchResponse(BaseModel):
    """Schema for batch job response."""
    batch_id: str
    name: Optional[str] = None
    status: str
    priority: str
    concurrency: int
    total_projects: int
    completed_projects: int = 0
    failed_projects: int = 0
    progress: str = "0%"
    success_rate: str = "0%"
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchProgressResponse(BaseModel):
    """Schema for batch progress response."""
    batch_id: str
    status: str
    total: int
    completed: int
    failed: int
    processed: int
    remaining: int
    progress_percentage: float
    success_rate: float


class BatchListResponse(BaseModel):
    """Schema for batch list response."""
    batches: List[BatchResponse]
    total: int


class BatchCancelResponse(BaseModel):
    """Schema for batch cancellation response."""
    batch_id: str
    status: str
    message: str
    tasks_cancelled: int
