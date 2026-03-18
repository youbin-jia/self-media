# backend/app/models/plugin.py
import uuid
from sqlalchemy import Column, String, Boolean, Text, JSON, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Plugin(Base):
    """插件模型"""
    __tablename__ = "plugins"
    __table_args__ = (
        UniqueConstraint('name', name='uq_plugin_name'),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    type = Column(String(50), nullable=False)  # material_source, llm_provider, etc.
    version = Column(String(20), nullable=False)
    description = Column(Text)
    author = Column(String(100))
    enabled = Column(Boolean, default=False, nullable=False)
    plugin_metadata = Column(JSON)  # Store module_path, class_name, file_path, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    configurations = relationship("PluginConfiguration", back_populates="plugin", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plugin(id={self.id}, name={self.name}, type={self.type}, enabled={self.enabled})>"


class PluginConfiguration(Base):
    """插件配置模型"""
    __tablename__ = "plugin_configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plugin_id = Column(String(36), ForeignKey("plugins.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    plugin = relationship("Plugin", back_populates="configurations")

    def __repr__(self):
        return f"<PluginConfiguration(plugin_id={self.plugin_id}, key={self.key})>"
