# backend/app/schemas/material.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class MaterialBase(BaseModel):
    material_type: Optional[str] = None  # "video", "image", "audio"
    type: Optional[str] = None  # Legacy field for backward compatibility
    source: str
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    local_path: str
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class MaterialCreate(MaterialBase):
    project_id: str
    file_hash: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    material_metadata: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None  # Legacy field for backward compatibility
    quality_score: Optional[float] = None


class MaterialResponse(MaterialBase):
    id: str
    project_id: str
    file_hash: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    material_metadata: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None  # Legacy field for backward compatibility
    quality_score: Optional[float] = None
    is_used: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MaterialWithTagSearch(BaseModel):
    """Material query with tag-based search"""
    tags: List[str]
    material_type: Optional[str] = None
    min_quality_score: Optional[float] = None
    limit: int = 20
