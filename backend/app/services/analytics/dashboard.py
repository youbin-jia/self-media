# backend/app/services/analytics/dashboard.py
"""
Dashboard service for providing dashboard-specific views and aggregations.
"""
from typing import Dict, Any, List, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import func, and_
from app.models.project import Project
from app.services.analytics.collector import MetricsCollector


class DashboardService:
    """
    Provides dashboard-specific views and aggregations.

    Extends MetricsCollector functionality with dashboard-focused methods
    for summary statistics, recent activity, and resource utilization.
    """

    def __init__(self, db: Union[Session, sessionmaker]):
        """
        Initialize DashboardService.

        Args:
            db: SQLAlchemy session or session factory
        """
        self.db = db
        self.metrics_collector = MetricsCollector(db)

    def _get_session(self) -> Session:
        """Get a database session."""
        if isinstance(self.db, sessionmaker):
            return self.db()
        return self.db

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard summary.

        Returns:
            Dict containing:
                - total_projects: Total count of all projects
                - status_distribution: Dict of status -> count
                - success_rate: Percentage of completed projects
                - average_processing_time: Average time for completed projects
                - recent_activities: List of recent project activities
                - active_projects: Number of projects currently processing
                - completed_this_week: Number of projects completed this week
        """
        # Get base statistics from MetricsCollector
        stats = self.metrics_collector.get_project_statistics()

        # Add dashboard-specific data
        recent_activities = self.get_recent_activities(limit=10)
        active_projects = self.get_active_projects_count()
        completed_this_week = self.get_completed_this_week()

        return {
            "total_projects": stats["total_projects"],
            "status_distribution": stats["status_distribution"],
            "success_rate": stats["success_rate"],
            "average_processing_time": stats["average_processing_time"],
            "recent_activities": recent_activities,
            "active_projects": active_projects,
            "completed_this_week": completed_this_week,
        }

    def get_recent_activities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent project activities.

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of dicts with project_id, title, status, updated_at
        """
        session = self._get_session()

        try:
            # Get recent projects ordered by updated_at
            projects = (
                session.query(Project)
                .filter(Project.updated_at.isnot(None))
                .order_by(Project.updated_at.desc())
                .limit(limit)
                .all()
            )

            activities = []
            for project in projects:
                activities.append({
                    "project_id": project.id,
                    "title": project.title,
                    "status": project.status,
                    "updated_at": project.updated_at,
                })

            return activities
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()

    def get_active_projects_count(self) -> int:
        """
        Get count of currently active projects.

        Active projects are those with 'processing' status.

        Returns:
            Count of active projects
        """
        session = self._get_session()

        try:
            count = (
                session.query(func.count(Project.id))
                .filter(Project.status == "processing")
                .scalar() or 0
            )
            return count
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()

    def get_completed_this_week(self) -> int:
        """
        Get count of projects completed this week.

        Returns:
            Count of projects completed in the current week
        """
        session = self._get_session()

        try:
            # Calculate start of current week (Monday)
            now = datetime.utcnow()
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

            count = (
                session.query(func.count(Project.id))
                .filter(
                    and_(
                        Project.status == "completed",
                        Project.updated_at >= start_of_week
                    )
                )
                .scalar() or 0
            )
            return count
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()

    def get_resource_utilization_summary(self) -> Dict[str, Any]:
        """
        Get resource utilization summary.

        Returns:
            Dict containing resource utilization metrics
        """
        session = self._get_session()

        try:
            # Count projects by status
            queued = (
                session.query(func.count(Project.id))
                .filter(Project.status == "pending")
                .scalar() or 0
            )

            processing = (
                session.query(func.count(Project.id))
                .filter(Project.status == "processing")
                .scalar() or 0
            )

            completed = (
                session.query(func.count(Project.id))
                .filter(Project.status == "completed")
                .scalar() or 0
            )

            failed = (
                session.query(func.count(Project.id))
                .filter(Project.status == "failed")
                .scalar() or 0
            )

            total = queued + processing + completed + failed

            return {
                "queued": queued,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "total": total,
                "utilization_percentage": (processing / total * 100) if total > 0 else 0,
            }
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()
