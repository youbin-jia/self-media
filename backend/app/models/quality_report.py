# backend/app/models/quality_report.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, DECIMAL, JSON
from sqlalchemy.sql import func
from app.database import Base


class QualityReport(Base):
    __tablename__ = "quality_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    report_type = Column(String(50))
    overall_score = Column(DECIMAL(5, 2))
    grade = Column(String(1))
    metrics = Column(JSON)
    issues = Column(JSON)
    recommendations = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<QualityReport(id={self.id}, project_id={self.project_id}, report_type={self.report_type})>"
