# backend/app/models/script.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ScriptStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class Script(Base):
    __tablename__ = "scripts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    content = Column(Text, nullable=False)
    version = Column(String(50), default="1.0")
    status = Column(Enum(ScriptStatus), default=ScriptStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="scripts")

    def __repr__(self):
        return f"<Script(id={self.id}, project_id={self.project_id}, status={self.status})>"
