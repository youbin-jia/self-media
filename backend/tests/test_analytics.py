# backend/tests/test_analytics.py
"""
Tests for MetricsCollector and analytics functionality.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.project import Project
from app.database import Base
from app.services.analytics.collector import MetricsCollector


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    @pytest.fixture
    def db_session(self):
        """Create an in-memory database session for testing."""
        SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create tables
        Base.metadata.create_all(bind=engine)

        session = TestingSessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def collector(self, db_session):
        """Create a MetricsCollector instance with test database."""
        return MetricsCollector(db=db_session)

    def test_get_project_statistics_empty_database(self, collector):
        """Test statistics when no projects exist."""
        stats = collector.get_project_statistics()

        assert stats["total_projects"] == 0
        assert stats["status_distribution"] == {}
        assert stats["success_rate"] == 0.0
        assert stats["average_processing_time"] is None

    def test_get_project_statistics_with_projects(self, collector, db_session):
        """Test statistics with various project states."""
        # Create projects with different statuses
        projects = [
            Project(title="Project 1", status="completed"),
            Project(title="Project 2", status="completed"),
            Project(title="Project 3", status="failed"),
            Project(title="Project 4", status="pending"),
            Project(title="Project 5", status="processing"),
        ]

        for project in projects:
            db_session.add(project)
        db_session.commit()

        stats = collector.get_project_statistics()

        assert stats["total_projects"] == 5
        assert stats["status_distribution"]["completed"] == 2
        assert stats["status_distribution"]["failed"] == 1
        assert stats["status_distribution"]["pending"] == 1
        assert stats["status_distribution"]["processing"] == 1

    def test_get_status_distribution(self, collector, db_session):
        """Test status distribution calculation."""
        # Create projects with different statuses
        projects = [
            Project(title="P1", status="completed"),
            Project(title="P2", status="completed"),
            Project(title="P3", status="completed"),
            Project(title="P4", status="failed"),
            Project(title="P5", status="pending"),
            Project(title="P6", status="processing"),
        ]

        for project in projects:
            db_session.add(project)
        db_session.commit()

        distribution = collector.get_status_distribution()

        assert distribution["completed"] == 3
        assert distribution["failed"] == 1
        assert distribution["pending"] == 1
        assert distribution["processing"] == 1

    def test_get_status_distribution_empty_database(self, collector):
        """Test status distribution when no projects exist."""
        distribution = collector.get_status_distribution()
        assert distribution == {}

    def test_get_success_rate_no_projects(self, collector):
        """Test success rate when no projects exist."""
        rate = collector.get_success_rate()
        assert rate == 0.0

    def test_get_success_rate_all_completed(self, collector, db_session):
        """Test success rate when all projects completed."""
        for i in range(5):
            db_session.add(Project(title=f"Project {i}", status="completed"))
        db_session.commit()

        rate = collector.get_success_rate()
        assert rate == 100.0

    def test_get_success_rate_all_failed(self, collector, db_session):
        """Test success rate when all projects failed."""
        for i in range(5):
            db_session.add(Project(title=f"Project {i}", status="failed"))
        db_session.commit()

        rate = collector.get_success_rate()
        assert rate == 0.0

    def test_get_success_rate_mixed_statuses(self, collector, db_session):
        """Test success rate with mixed project statuses."""
        # 8 completed, 2 failed = 80% success rate
        for i in range(8):
            db_session.add(Project(title=f"Completed {i}", status="completed"))
        for i in range(2):
            db_session.add(Project(title=f"Failed {i}", status="failed"))
        db_session.commit()

        rate = collector.get_success_rate()
        assert rate == 80.0

    def test_get_success_rate_ignores_incomplete_projects(self, collector, db_session):
        """Test that success rate only considers completed/failed projects."""
        # Create projects with various statuses
        for i in range(6):
            db_session.add(Project(title=f"Completed {i}", status="completed"))
        for i in range(2):
            db_session.add(Project(title=f"Failed {i}", status="failed"))
        # These should not affect success rate
        for i in range(10):
            db_session.add(Project(title=f"Pending {i}", status="pending"))
        for i in range(5):
            db_session.add(Project(title=f"Processing {i}", status="processing"))
        db_session.commit()

        rate = collector.get_success_rate()
        # 6 completed, 2 failed = 6/8 = 75%
        assert rate == 75.0

    def test_get_average_processing_time_no_projects(self, collector):
        """Test average processing time when no completed projects exist."""
        avg_time = collector.get_average_processing_time()
        assert avg_time is None

    def test_get_average_processing_time_completed_projects(self, collector, db_session):
        """Test average processing time for completed projects."""
        # Create completed projects with processing times
        now = datetime.utcnow()

        # Project 1: 10 seconds
        p1 = Project(title="P1", status="completed")
        p1.created_at = now - timedelta(seconds=10)
        p1.updated_at = now
        db_session.add(p1)

        # Project 2: 20 seconds
        p2 = Project(title="P2", status="completed")
        p2.created_at = now - timedelta(seconds=20)
        p2.updated_at = now
        db_session.add(p2)

        # Project 3: 30 seconds
        p3 = Project(title="P3", status="completed")
        p3.created_at = now - timedelta(seconds=30)
        p3.updated_at = now
        db_session.add(p3)

        db_session.commit()

        avg_time = collector.get_average_processing_time()
        # Average: (10 + 20 + 30) / 3 = 20 seconds
        assert avg_time is not None
        assert abs(avg_time - 20.0) < 1.0  # Allow 1 second tolerance

    def test_get_average_processing_time_ignores_incomplete(self, collector, db_session):
        """Test that average processing time only considers completed projects."""
        now = datetime.utcnow()

        # Completed project
        p1 = Project(title="P1", status="completed")
        p1.created_at = now - timedelta(seconds=10)
        p1.updated_at = now
        db_session.add(p1)

        # Failed project - should be ignored
        p2 = Project(title="P2", status="failed")
        p2.created_at = now - timedelta(seconds=100)
        p2.updated_at = now
        db_session.add(p2)

        # Pending project - should be ignored
        p3 = Project(title="P3", status="pending")
        p3.created_at = now - timedelta(seconds=200)
        db_session.add(p3)

        db_session.commit()

        avg_time = collector.get_average_processing_time()
        # Should only consider the completed project (10 seconds)
        assert avg_time is not None
        assert abs(avg_time - 10.0) < 1.0

    def test_get_projects_timeline_daily(self, collector, db_session):
        """Test daily timeline generation."""
        now = datetime.utcnow()
        today = now.date()

        # Create projects on different days
        for i in range(3):
            p = Project(title=f"Today {i}", status="completed")
            p.created_at = now - timedelta(hours=i)
            db_session.add(p)

        for i in range(2):
            p = Project(title=f"Yesterday {i}", status="completed")
            p.created_at = now - timedelta(days=1, hours=i)
            db_session.add(p)

        db_session.commit()

        timeline = collector.get_projects_timeline(period="daily", days=7)

        assert len(timeline) == 7
        # Most recent day should have 3 projects
        assert timeline[-1]["count"] == 3
        # Yesterday should have 2 projects
        assert timeline[-2]["count"] == 2

    def test_get_projects_timeline_weekly(self, collector, db_session):
        """Test weekly timeline generation."""
        now = datetime.utcnow()

        # Create projects in different weeks
        for i in range(5):
            p = Project(title=f"This week {i}", status="completed")
            p.created_at = now - timedelta(days=i)
            db_session.add(p)

        for i in range(3):
            p = Project(title=f"Last week {i}", status="completed")
            p.created_at = now - timedelta(weeks=1, days=i)
            db_session.add(p)

        db_session.commit()

        timeline = collector.get_projects_timeline(period="weekly", weeks=4)

        assert len(timeline) == 4
        # Current week should have 5 projects
        assert timeline[-1]["count"] == 5
        # Last week should have 3 projects
        assert timeline[-2]["count"] == 3

    def test_get_projects_timeline_monthly(self, collector, db_session):
        """Test monthly timeline generation."""
        now = datetime.utcnow()

        # Create projects in different months
        for i in range(4):
            p = Project(title=f"This month {i}", status="completed")
            p.created_at = now - timedelta(days=i)
            db_session.add(p)

        for i in range(2):
            p = Project(title=f"Last month {i}", status="completed")
            p.created_at = now - timedelta(days=32 + i)
            db_session.add(p)

        db_session.commit()

        timeline = collector.get_projects_timeline(period="monthly", months=6)

        assert len(timeline) == 6
        # Current month should have at least 4 projects
        assert timeline[-1]["count"] >= 4

    def test_get_projects_timeline_empty_database(self, collector):
        """Test timeline generation when no projects exist."""
        timeline = collector.get_projects_timeline(period="daily", days=7)

        assert len(timeline) == 7
        # All counts should be 0
        for item in timeline:
            assert item["count"] == 0

    def test_get_projects_timeline_default_parameters(self, collector):
        """Test timeline generation with default parameters."""
        timeline = collector.get_projects_timeline()

        # Should default to daily for 7 days
        assert len(timeline) == 7

    def test_get_projects_timeline_includes_date_field(self, collector, db_session):
        """Test that timeline includes date field."""
        now = datetime.utcnow()
        p = Project(title="P1", status="completed")
        p.created_at = now
        db_session.add(p)
        db_session.commit()

        timeline = collector.get_projects_timeline(period="daily", days=7)

        assert len(timeline) == 7
        for item in timeline:
            assert "date" in item
            assert "count" in item

    def test_get_project_statistics_includes_all_metrics(self, collector, db_session):
        """Test that get_project_statistics includes all required metrics."""
        now = datetime.utcnow()

        # Create various projects
        projects = [
            Project(title="Completed 1", status="completed"),
            Project(title="Completed 2", status="completed"),
            Project(title="Failed 1", status="failed"),
            Project(title="Pending 1", status="pending"),
        ]

        for i, project in enumerate(projects):
            project.created_at = now - timedelta(seconds=10 * (i + 1))
            if project.status in ["completed", "failed"]:
                project.updated_at = now
            db_session.add(project)
        db_session.commit()

        stats = collector.get_project_statistics()

        # Verify all required fields are present
        assert "total_projects" in stats
        assert "status_distribution" in stats
        assert "success_rate" in stats
        assert "average_processing_time" in stats

        # Verify values
        assert stats["total_projects"] == 4
        assert isinstance(stats["status_distribution"], dict)
        assert isinstance(stats["success_rate"], float)
        # Average processing time should be a float or None
        assert stats["average_processing_time"] is None or isinstance(
            stats["average_processing_time"], (int, float)
        )

    def test_metrics_collector_with_session_factory(self):
        """Test that MetricsCollector can be initialized with session factory."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        # Should accept both session and session factory
        collector1 = MetricsCollector(db=TestingSessionLocal)
        collector2 = MetricsCollector(db=TestingSessionLocal())

        assert collector1 is not None
        assert collector2 is not None


class TestMetricsCollectorEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def db_session(self):
        """Create an in-memory database session for testing."""
        SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        session = TestingSessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def collector(self, db_session):
        """Create a MetricsCollector instance with test database."""
        return MetricsCollector(db=db_session)

    def test_success_rate_with_only_pending_projects(self, collector, db_session):
        """Test success rate when only pending projects exist."""
        for i in range(5):
            db_session.add(Project(title=f"Pending {i}", status="pending"))
        db_session.commit()

        rate = collector.get_success_rate()
        # No completed/failed projects, should return 0
        assert rate == 0.0

    def test_processing_time_with_null_updated_at(self, collector, db_session):
        """Test average processing time when updated_at is null."""
        now = datetime.utcnow()

        # Completed project without updated_at
        p = Project(title="P1", status="completed")
        p.created_at = now - timedelta(seconds=100)
        p.updated_at = None
        db_session.add(p)
        db_session.commit()

        avg_time = collector.get_average_processing_time()
        # Should handle gracefully
        assert avg_time is None or isinstance(avg_time, (int, float))

    def test_timeline_with_future_dates(self, collector, db_session):
        """Test timeline generation with projects created in the future."""
        now = datetime.utcnow()

        # Project created in the future
        p = Project(title="Future", status="completed")
        p.created_at = now + timedelta(days=5)
        db_session.add(p)
        db_session.commit()

        timeline = collector.get_projects_timeline(period="daily", days=7)

        # Should handle gracefully
        assert len(timeline) == 7

    def test_timeline_with_very_old_projects(self, collector, db_session):
        """Test timeline generation with very old projects."""
        now = datetime.utcnow()

        # Project created 100 days ago
        p = Project(title="Old", status="completed")
        p.created_at = now - timedelta(days=100)
        db_session.add(p)
        db_session.commit()

        timeline = collector.get_projects_timeline(period="daily", days=7)

        # Old project should not appear in recent timeline
        assert len(timeline) == 7
        total_count = sum(item["count"] for item in timeline)
        assert total_count == 0

    def test_status_distribution_with_null_status(self, collector, db_session):
        """Test status distribution when status is null."""
        # Project without status
        p = Project(title="No Status", status=None)
        db_session.add(p)
        db_session.commit()

        distribution = collector.get_status_distribution()

        # Should handle null status gracefully
        assert isinstance(distribution, dict)
