# backend/app/services/analytics/collector.py
"""
MetricsCollector for aggregating and analyzing project metrics.
"""
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import func, and_
from app.models.project import Project


class MetricsCollector:
    """
    Collects and aggregates metrics from Project data.

    Derives metrics from existing Project model without requiring
    a separate metrics storage table.
    """

    def __init__(self, db: Union[Session, sessionmaker]):
        """
        Initialize MetricsCollector.

        Args:
            db: SQLAlchemy session or session factory
        """
        self.db = db

    def _get_session(self) -> Session:
        """Get a database session."""
        if isinstance(self.db, sessionmaker):
            return self.db()
        return self.db

    def get_project_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive project statistics.

        Returns:
            Dict containing:
                - total_projects: Total count of all projects
                - status_distribution: Dict of status -> count
                - success_rate: Percentage of completed projects (vs failed)
                - average_processing_time: Average time for completed projects
        """
        session = self._get_session()

        try:
            # Total projects count
            total = session.query(func.count(Project.id)).scalar() or 0

            # Status distribution
            status_dist = self.get_status_distribution()

            # Success rate
            success_rate = self.get_success_rate()

            # Average processing time
            avg_time = self.get_average_processing_time()

            return {
                "total_projects": total,
                "status_distribution": status_dist,
                "success_rate": success_rate,
                "average_processing_time": avg_time,
            }
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()

    def get_status_distribution(self) -> Dict[str, int]:
        """
        Get distribution of projects by status.

        Returns:
            Dict mapping status to count
        """
        session = self._get_session()

        try:
            # Query status counts
            results = (
                session.query(
                    Project.status,
                    func.count(Project.id).label("count")
                )
                .filter(Project.status.isnot(None))
                .group_by(Project.status)
                .all()
            )

            # Convert to dict
            return {status: count for status, count in results}
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()

    def get_success_rate(self) -> float:
        """
        Calculate success rate of completed projects.

        Only considers projects with 'completed' or 'failed' status.
        Pending or processing projects are excluded.

        Returns:
            Success rate as percentage (0-100)
        """
        session = self._get_session()

        try:
            # Count completed and failed projects
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

            total_finished = completed + failed

            if total_finished == 0:
                return 0.0

            return (completed / total_finished) * 100.0
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()

    def get_average_processing_time(self) -> Optional[float]:
        """
        Calculate average processing time for completed projects.

        Processing time is calculated as (updated_at - created_at).
        Only considers projects with 'completed' status.

        Returns:
            Average processing time in seconds, or None if no completed projects
        """
        session = self._get_session()

        try:
            # Get completed projects with valid timestamps
            projects = (
                session.query(Project)
                .filter(
                    and_(
                        Project.status == "completed",
                        Project.created_at.isnot(None),
                        Project.updated_at.isnot(None)
                    )
                )
                .all()
            )

            if not projects:
                return None

            # Calculate processing times
            times = []
            for project in projects:
                if project.created_at and project.updated_at:
                    delta = project.updated_at - project.created_at
                    times.append(delta.total_seconds())

            if not times:
                return None

            return sum(times) / len(times)
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()

    def get_projects_timeline(
        self,
        period: str = "daily",
        days: Optional[int] = None,
        weeks: Optional[int] = None,
        months: Optional[int] = None
    ) -> List[Dict]:
        """
        Get timeline of projects created over time.

        Args:
            period: Time period - "daily", "weekly", or "monthly"
            days: Number of days for daily period (default: 7)
            weeks: Number of weeks for weekly period (default: 4)
            months: Number of months for monthly period (default: 6)

        Returns:
            List of dicts with 'date' and 'count' fields
        """
        # Set default values
        if period == "daily":
            num_periods = days or 7
        elif period == "weekly":
            num_periods = weeks or 4
        elif period == "monthly":
            num_periods = months or 6
        else:
            # Default to daily
            period = "daily"
            num_periods = 7

        session = self._get_session()

        try:
            now = datetime.utcnow()
            timeline = []

            for i in range(num_periods):
                if period == "daily":
                    # Calculate day range
                    end_date = now - timedelta(days=i)
                    start_date = now - timedelta(days=i+1)

                    # Use date for display
                    date_str = end_date.strftime("%Y-%m-%d")

                elif period == "weekly":
                    # Calculate week range
                    end_date = now - timedelta(weeks=i)
                    start_date = now - timedelta(weeks=i+1)

                    # Use week start date for display
                    date_str = end_date.strftime("%Y-%m-%d")

                elif period == "monthly":
                    # Calculate month range
                    end_date = now - timedelta(days=i*30)
                    start_date = now - timedelta(days=(i+1)*30)

                    # Use month for display
                    date_str = end_date.strftime("%Y-%m")

                # Count projects created in this period
                count = (
                    session.query(func.count(Project.id))
                    .filter(
                        and_(
                            Project.created_at >= start_date,
                            Project.created_at < end_date
                        )
                    )
                    .scalar() or 0
                )

                timeline.append({
                    "date": date_str,
                    "count": count
                })

            # Reverse to get chronological order
            timeline.reverse()
            return timeline
        finally:
            if isinstance(self.db, sessionmaker):
                session.close()
