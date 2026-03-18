# backend/tests/test_performance.py
"""
Performance tests for database indexes and query optimization.
Tests verify that required indexes exist and queries perform efficiently.
"""
import pytest
import time
from sqlalchemy import inspect, text
from app.database import Base
from app.models.user import User
from app.models.project import Project
from app.models.material import Material
from app.models.task import Task


def get_table_indexes(engine, table_name: str) -> list:
    """Get list of indexed columns for a table."""
    inspector = inspect(engine)
    indexes = []
    for idx in inspector.get_indexes(table_name):
        for col in idx['column_names']:
            indexes.append(col)
    return indexes


class TestDatabaseIndexes:
    """Test that required indexes exist on database tables."""

    def test_project_status_index_exists(self, test_db):
        """Project.status should have an index for status filtering."""
        # Get the engine from the test database session
        engine = test_db.get_bind()
        indexes = get_table_indexes(engine, 'projects')
        assert 'status' in indexes, "Missing index on projects.status"

    def test_project_created_at_index_exists(self, test_db):
        """Project.created_at should have an index for chronological queries."""
        engine = test_db.get_bind()
        indexes = get_table_indexes(engine, 'projects')
        assert 'created_at' in indexes, "Missing index on projects.created_at"

    def test_material_type_index_exists(self, test_db):
        """Material.material_type should have an index for type filtering."""
        engine = test_db.get_bind()
        indexes = get_table_indexes(engine, 'materials')
        # Check for both material_type and type (legacy)
        assert 'material_type' in indexes or 'type' in indexes, \
            "Missing index on materials.material_type"

    def test_task_status_index_exists(self, test_db):
        """Task.status should have an index for task queue queries."""
        engine = test_db.get_bind()
        indexes = get_table_indexes(engine, 'tasks')
        assert 'status' in indexes, "Missing index on tasks.status"

    def test_existing_indexes_maintained(self, test_db):
        """Existing indexes on user_id, owner_id, project_id should be maintained."""
        engine = test_db.get_bind()

        # Projects table
        project_indexes = get_table_indexes(engine, 'projects')
        assert 'owner_id' in project_indexes, "Missing index on projects.owner_id"

        # Materials table
        material_indexes = get_table_indexes(engine, 'materials')
        assert 'project_id' in material_indexes, "Missing index on materials.project_id"
        assert 'user_id' in material_indexes, "Missing index on materials.user_id"

        # Tasks table
        task_indexes = get_table_indexes(engine, 'tasks')
        assert 'user_id' in task_indexes, "Missing index on tasks.user_id"


class TestQueryPerformance:
    """Test query performance with indexes."""

    @pytest.fixture
    def setup_test_data(self, test_db):
        """Create test data for performance testing."""
        # Create test user
        user = User(
            username="perf_test_user",
            email="perf@test.com",
            hashed_password="test_hash"
        )
        test_db.add(user)
        test_db.commit()

        # Create test projects with various statuses
        statuses = ["draft", "in_progress", "completed", "archived"]
        for i in range(100):
            project = Project(
                title=f"Test Project {i}",
                status=statuses[i % len(statuses)],
                owner_id=user.id
            )
            test_db.add(project)

        test_db.commit()

        # Create test materials
        for i in range(50):
            material = Material(
                project_id=1,  # Will be updated after commit
                user_id=user.id,
                material_type=["video", "image", "audio"][i % 3],
                source="test",
                local_path=f"/test/path/{i}"
            )
            test_db.add(material)

        # Create test tasks
        for i in range(30):
            task = Task(
                project_id=1,
                user_id=user.id,
                task_type="test_task",
                status=["pending", "processing", "completed"][i % 3]
            )
            test_db.add(task)

        test_db.commit()
        return user

    def test_project_status_filter_performance(self, test_db, setup_test_data):
        """Query by project status should be fast with index."""
        start_time = time.time()

        projects = test_db.query(Project).filter(
            Project.status == "in_progress"
        ).all()

        elapsed = (time.time() - start_time) * 1000  # Convert to ms

        # Query should complete in under 100ms
        assert elapsed < 100, f"Query took {elapsed}ms, expected < 100ms"
        assert len(projects) > 0

    def test_project_chronological_query_performance(self, test_db, setup_test_data):
        """Query by created_at should be fast with index."""
        start_time = time.time()

        projects = test_db.query(Project).order_by(
            Project.created_at.desc()
        ).limit(20).all()

        elapsed = (time.time() - start_time) * 1000

        # Query should complete in under 100ms
        assert elapsed < 100, f"Query took {elapsed}ms, expected < 100ms"
        assert len(projects) == 20

    def test_material_type_filter_performance(self, test_db, setup_test_data):
        """Query by material type should be fast with index."""
        start_time = time.time()

        materials = test_db.query(Material).filter(
            Material.material_type == "video"
        ).all()

        elapsed = (time.time() - start_time) * 1000

        # Query should complete in under 100ms
        assert elapsed < 100, f"Query took {elapsed}ms, expected < 100ms"

    def test_task_status_filter_performance(self, test_db, setup_test_data):
        """Query by task status should be fast with index."""
        start_time = time.time()

        tasks = test_db.query(Task).filter(
            Task.status == "pending"
        ).all()

        elapsed = (time.time() - start_time) * 1000

        # Query should complete in under 100ms
        assert elapsed < 100, f"Query took {elapsed}ms, expected < 100ms"

    def test_combined_filter_with_pagination(self, test_db, setup_test_data):
        """Combined filter queries with pagination should be efficient."""
        start_time = time.time()

        # Common pattern: filter by owner and status, order by date, paginate
        projects = test_db.query(Project).filter(
            Project.owner_id == setup_test_data.id,
            Project.status != "deleted"
        ).order_by(
            Project.created_at.desc()
        ).offset(10).limit(10).all()

        elapsed = (time.time() - start_time) * 1000

        # Query should complete in under 100ms
        assert elapsed < 100, f"Query took {elapsed}ms, expected < 100ms"
        assert len(projects) == 10
