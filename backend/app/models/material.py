# backend/app/models/material.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    type = Column(String(20))
    source = Column(String(50))
    source_url = Column(Text)
    local_path = Column(Text)
    material_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Material(id={self.id}, type={self.type})>"
