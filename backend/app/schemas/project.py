# backend/app/schemas/project.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ProjectCreate(ProjectBase):
    topic_source: Optional[str] = None
    topic_title: Optional[str] = None
    topic_hot_score: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = None
    current_step: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectResponse(ProjectBase):
    id: str
    status: str
    current_step: str
    created_at: datetime
    updated_at: Optional[datetime]
    topic_source: Optional[str]
    topic_title: Optional[str]
    topic_hot_score: Optional[int]
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True
