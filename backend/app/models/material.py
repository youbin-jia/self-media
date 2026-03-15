# backend/app/models/material.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class MaterialType(str, enum.Enum):
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    TEXT = "text"


class Material(Base):
    __tablename__ = "materials"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    type = Column(Enum(MaterialType), nullable=False)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=True)
    duration = Column(Float, nullable=True)  # Duration in seconds for video/audio
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="materials")

    def __repr__(self):
        return f"<Material(id={self.id}, name={self.name}, type={self.type})>"
