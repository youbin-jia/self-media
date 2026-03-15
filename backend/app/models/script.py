# backend/app/models/script.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base


class Script(Base):
    __tablename__ = "scripts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    version = Column(Integer)
    outline = Column(Text)
    full_script = Column(Text)
    segments = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_approved = Column(Boolean)

    def __repr__(self):
        return f"<Script(id={self.id}, project_id={self.project_id})>"
