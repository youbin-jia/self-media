# backend/app/models/project.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    status = Column(String(50))
    current_step = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    topic_source = Column(String(50))
    topic_title = Column(Text)
    topic_hot_score = Column(Integer)
    project_metadata = Column(JSON)

    # Relationships using backref
    scripts = relationship("Script", backref="project")
    materials = relationship("Material", backref="project")
    tasks = relationship("Task", backref="project")
    quality_reports = relationship("QualityReport", backref="project")

    def __repr__(self):
        return f"<Project(id={self.id}, title={self.title}, status={self.status})>"
