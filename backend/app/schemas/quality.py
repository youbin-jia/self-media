# backend/app/schemas/quality.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal


class QualityReportBase(BaseModel):
    report_type: str
    overall_score: Optional[Decimal] = None
    grade: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    issues: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None


class QualityReportCreate(QualityReportBase):
    project_id: str


class QualityReportResponse(QualityReportBase):
    id: str
    project_id: str
    created_at: datetime

    class Config:
        from_attributes = True
