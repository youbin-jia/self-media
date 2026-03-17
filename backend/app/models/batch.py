# backend/app/models/batch.py
"""
BatchJob model for batch video processing with UUID primary key
and Redis state management for real-time tracking.
"""
import uuid
from sqlalchemy import Column, String, DateTime, JSON, Integer, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class BatchJob(Base):
    """
    BatchJob model for tracking batch video generation tasks.

    Key features:
    - UUID primary key (not Integer) for distributed systems
    - Redis state management for real-time tracking
    - task_ids field for tracking individual Celery tasks
    - concurrency field for dynamic scheduling
    """
    __tablename__ = "batch_jobs"

    # UUID primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # User association for data isolation
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Batch identification
    name = Column(String(255), nullable=True)  # Optional user-friendly name

    # Project and task tracking
    project_ids = Column(JSON, nullable=False, default=list)  # List of project UUIDs
    task_ids = Column(JSON, nullable=True, default=list)  # List of Celery task IDs

    # Status and priority
    status = Column(String(20), nullable=False, default="queued")  # queued, running, completed, failed, cancelled
    priority = Column(String(10), nullable=False, default="normal")  # high, normal, low

    # Concurrency control
    concurrency = Column(Integer, nullable=False, default=3)  # Number of parallel tasks

    # Progress tracking
    total_projects = Column(Integer, nullable=False, default=0)
    completed_projects = Column(Integer, nullable=False, default=0)
    failed_projects = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_messages = Column(JSON, nullable=True, default=list)  # [{project_id, error}]

    def __repr__(self):
        return f"<BatchJob(id={self.id}, status={self.status}, total={self.total_projects})>"

    @property
    def progress_percentage(self) -> float:
        """Calculate progress as a percentage."""
        if self.total_projects == 0:
            return 0.0
        return round(((self.completed_projects + self.failed_projects) / self.total_projects) * 100, 1)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_projects == 0:
            return 0.0
        return round((self.completed_projects / self.total_projects) * 100, 1)

    @property
    def is_active(self) -> bool:
        """Check if batch is still active (not completed, failed, or cancelled)."""
        return self.status in ("queued", "running")

    @property
    def is_finished(self) -> bool:
        """Check if batch has finished (completed, failed, or cancelled)."""
        return self.status in ("completed", "failed", "cancelled")

    def to_dict(self) -> dict:
        """Convert batch job to dictionary for API responses."""
        return {
            "batch_id": self.id,
            "name": self.name,
            "status": self.status,
            "priority": self.priority,
            "concurrency": self.concurrency,
            "total_projects": self.total_projects,
            "completed_projects": self.completed_projects,
            "failed_projects": self.failed_projects,
            "progress": f"{self.progress_percentage}%",
            "success_rate": f"{self.success_rate}%",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BatchStatus:
    """Enumeration of valid batch statuses."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def all(cls) -> list:
        return [cls.QUEUED, cls.RUNNING, cls.COMPLETED, cls.FAILED, cls.CANCELLED]

    @classmethod
    def is_valid(cls, status: str) -> bool:
        return status in cls.all()


class BatchPriority:
    """Enumeration of valid batch priorities."""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"

    @classmethod
    def all(cls) -> list:
        return [cls.HIGH, cls.NORMAL, cls.LOW]

    @classmethod
    def is_valid(cls, priority: str) -> bool:
        return priority in cls.all()

    @classmethod
    def to_celery_priority(cls, priority: str) -> int:
        """Convert priority to Celery task priority (0-9)."""
        mapping = {
            cls.HIGH: 9,
            cls.NORMAL: 5,
            cls.LOW: 1,
        }
        return mapping.get(priority, 5)
