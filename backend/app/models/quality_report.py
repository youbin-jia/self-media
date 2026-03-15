# backend/app/models/quality_report.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Integer, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class QualityReportStatus(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class QualityReport(Base):
    __tablename__ = "quality_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    status = Column(Enum(QualityReportStatus), default=QualityReportStatus.PENDING)
    overall_score = Column(Float, nullable=True)  # 0-100 score
    details = Column(JSON, nullable=True)  # Detailed quality metrics
    issues = Column(JSON, nullable=True)  # List of issues found
    recommendations = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="quality_reports")

    def __repr__(self):
        return f"<QualityReport(id={self.id}, project_id={self.project_id}, status={self.status})>"
