# backend/app/schemas/material.py
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class MaterialBase(BaseModel):
    type: str  # image, video, audio
    source: str


class MaterialCreate(MaterialBase):
    project_id: str
    source_url: Optional[str] = None
    local_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MaterialResponse(MaterialBase):
    id: str
    project_id: str
    source_url: Optional[str]
    local_path: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
