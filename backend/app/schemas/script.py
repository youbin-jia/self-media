# backend/app/schemas/script.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class ScriptSegment(BaseModel):
    id: str
    text: str
    duration: float  # seconds
    emotion: Optional[str] = None
    material_ids: List[str] = []


class ScriptBase(BaseModel):
    outline: Optional[str] = None
    full_script: Optional[str] = None
    segments: Optional[List[ScriptSegment]] = None


class ScriptCreate(ScriptBase):
    project_id: str


class ScriptUpdate(BaseModel):
    outline: Optional[str] = None
    full_script: Optional[str] = None
    segments: Optional[List[ScriptSegment]] = None
    is_approved: Optional[bool] = None


class ScriptResponse(ScriptBase):
    id: str
    project_id: str
    version: int
    created_at: datetime
    is_approved: bool

    class Config:
        from_attributes = True
