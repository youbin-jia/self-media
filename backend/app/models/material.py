# backend/app/models/material.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Integer, Float, Boolean, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        UniqueConstraint('project_id', 'file_hash', name='uq_material_project_hash'),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Material information
    material_type = Column(String(20))  # "video", "image", "audio"
    type = Column(String(20))  # Legacy field, kept for backward compatibility
    source = Column(String(50), nullable=False)  # "pexels", "local", "ai_generated"
    source_id = Column(String(100))  # External material ID
    source_url = Column(Text)  # Original URL

    # Local storage
    local_path = Column(Text, nullable=False)
    file_hash = Column(String(64), index=True)  # SHA256 hash for deduplication (unique per project)

    # Metadata
    duration = Column(Float)  # Duration in seconds
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)  # Bytes
    material_metadata = Column(JSON)  # Extended metadata

    # Tag system
    tags = Column(JSON)  # ["nature", "landscape", "sunset"]
    description = Column(String(500))

    # Quality scoring
    quality_score = Column(Float)  # 0-100
    is_used = Column(Boolean, default=False)  # Whether used in project

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Material(id={self.id}, type={self.material_type or self.type})>"
