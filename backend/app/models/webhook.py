# backend/app/models/webhook.py
import uuid
from sqlalchemy import Column, String, Boolean, Text, JSON, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Webhook(Base):
    """Webhook模型"""
    __tablename__ = "webhooks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, nullable=False, default=list)  # ["project.completed", "project.failed"]
    secret = Column(String(255))  # For signature verification
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Webhook(id={self.id}, name={self.name}, url={self.url})>"


class WebhookDelivery(Base):
    """Webhook投递记录模型"""
    __tablename__ = "webhook_deliveries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_id = Column(String(36), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, success, failed, retrying
    response_code = Column(Integer)
    response_body = Column(Text)
    error_message = Column(Text)
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    next_retry_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    def __repr__(self):
        return f"<WebhookDelivery(id={self.id}, webhook_id={self.webhook_id}, status={self.status})>"
