# backend/app/services/analytics/__init__.py
"""
Analytics services for metrics collection and reporting.
"""

from app.services.analytics.collector import MetricsCollector

__all__ = ["MetricsCollector"]
