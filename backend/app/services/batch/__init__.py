# backend/app/services/batch/__init__.py
"""
Batch processing services including intelligent scheduling.
"""
from app.services.batch.scheduler import SmartScheduler

__all__ = ["SmartScheduler"]
