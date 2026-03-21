import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.sql import func
from app.database import Base


class ScriptHistory(Base):
    __tablename__ = "script_histories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    script_id = Column(String(36), ForeignKey("scripts.id"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    outline = Column(Text)
    full_script = Column(Text)
    segments = Column(JSON)
    source = Column(String(50), default="manual_edit")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<ScriptHistory(id={self.id}, project_id={self.project_id}, version={self.version})>"

