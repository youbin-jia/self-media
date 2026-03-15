# backend/app/models/task.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Integer, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class TaskType(str, enum.Enum):
    SCRIPT_GENERATION = "script_generation"
    MATERIAL_COLLECTION = "material_collection"
    VIDEO_EDITING = "video_editing"
    QUALITY_CHECK = "quality_check"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    progress = Column(Integer, default=0)  # 0-100 percentage
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)  # Store task result data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="tasks")

    def __repr__(self):
        return f"<Task(id={self.id}, type={self.type}, status={self.status})>"
