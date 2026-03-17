# backend/tests/test_batch.py
"""
Tests for BatchJob model and Redis state management.
"""
import pytest
import uuid
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.models.batch import BatchJob, BatchStatus, BatchPriority
from app.services.batch_state import BatchStateManager, get_batch_state_manager


class TestBatchJobModel:
    """Tests for the BatchJob SQLAlchemy model."""

    def test_batch_job_uuid_field_is_string_36(self):
        """Test that BatchJob ID field is configured for UUID strings."""
        # Verify the column is configured for UUID (String(36))
        from sqlalchemy import inspect
        mapper = inspect(BatchJob)
        id_column = mapper.columns['id']
        assert id_column.type.length == 36
        # Default should be a callable that generates UUID strings
        assert callable(id_column.default.arg)

    def test_batch_job_default_column_values(self):
        """Test that BatchJob columns have correct default configurations."""
        from sqlalchemy import inspect
        mapper = inspect(BatchJob)

        # Check default values are configured correctly
        status_col = mapper.columns['status']
        assert status_col.default.arg == "pending"

        priority_col = mapper.columns['priority']
        assert priority_col.default.arg == "normal"

        concurrency_col = mapper.columns['concurrency']
        assert concurrency_col.default.arg == 3

        total_col = mapper.columns['total_projects']
        assert total_col.default.arg == 0

        completed_col = mapper.columns['completed_projects']
        assert completed_col.default.arg == 0

        failed_col = mapper.columns['failed_projects']
        assert failed_col.default.arg == 0

    def test_batch_job_custom_values(self):
        """Test BatchJob with custom values."""
        project_ids = ["proj-1", "proj-2", "proj-3"]
        batch = BatchJob(
            id=str(uuid.uuid4()),
            name="Test Batch",
            project_ids=project_ids,
            total_projects=len(project_ids),
            status=BatchStatus.RUNNING,
            priority=BatchPriority.HIGH,
            concurrency=5,
        )
        assert batch.name == "Test Batch"
        assert batch.total_projects == 3
        assert batch.status == "running"
        assert batch.priority == "high"
        assert batch.concurrency == 5

    def test_progress_percentage(self):
        """Test progress calculation."""
        batch = BatchJob(total_projects=10, completed_projects=3, failed_projects=2)
        assert batch.progress_percentage == 50.0  # (3+2)/10 * 100

    def test_progress_percentage_zero_total(self):
        """Test progress when total is zero."""
        batch = BatchJob(total_projects=0)
        assert batch.progress_percentage == 0.0

    def test_success_rate(self):
        """Test success rate calculation."""
        batch = BatchJob(total_projects=10, completed_projects=8, failed_projects=2)
        assert batch.success_rate == 80.0  # 8/10 * 100

    def test_success_rate_zero_total(self):
        """Test success rate when total is zero."""
        batch = BatchJob(total_projects=0)
        assert batch.success_rate == 0.0

    def test_is_active(self):
        """Test is_active property."""
        batch = BatchJob(status=BatchStatus.PENDING)
        assert batch.is_active is True

        batch.status = BatchStatus.RUNNING
        assert batch.is_active is True

        batch.status = BatchStatus.COMPLETED
        assert batch.is_active is False

        batch.status = BatchStatus.FAILED
        assert batch.is_active is False

        batch.status = BatchStatus.CANCELLED
        assert batch.is_active is False

    def test_is_finished(self):
        """Test is_finished property."""
        batch = BatchJob(status=BatchStatus.PENDING)
        assert batch.is_finished is False

        batch.status = BatchStatus.COMPLETED
        assert batch.is_finished is True

        batch.status = BatchStatus.FAILED
        assert batch.is_finished is True

        batch.status = BatchStatus.CANCELLED
        assert batch.is_finished is True

    def test_to_dict(self):
        """Test to_dict conversion."""
        batch = BatchJob(
            id="test-batch-id",
            name="Test",
            status=BatchStatus.RUNNING,
            total_projects=10,
            completed_projects=5,
            failed_projects=1,
        )
        data = batch.to_dict()

        assert data["batch_id"] == "test-batch-id"
        assert data["name"] == "Test"
        assert data["status"] == "running"
        assert data["total_projects"] == 10
        assert data["completed_projects"] == 5
        assert data["failed_projects"] == 1
        assert "progress" in data
        assert "success_rate" in data


class TestBatchStatus:
    """Tests for BatchStatus enumeration."""

    def test_all_statuses(self):
        """Test that all statuses are defined."""
        all_statuses = BatchStatus.all()
        assert "pending" in all_statuses
        assert "running" in all_statuses
        assert "completed" in all_statuses
        assert "failed" in all_statuses
        assert "cancelled" in all_statuses

    def test_is_valid(self):
        """Test status validation."""
        assert BatchStatus.is_valid("pending") is True
        assert BatchStatus.is_valid("running") is True
        assert BatchStatus.is_valid("completed") is True
        assert BatchStatus.is_valid("failed") is True
        assert BatchStatus.is_valid("cancelled") is True
        assert BatchStatus.is_valid("invalid") is False


class TestBatchPriority:
    """Tests for BatchPriority enumeration."""

    def test_all_priorities(self):
        """Test that all priorities are defined."""
        all_priorities = BatchPriority.all()
        assert "high" in all_priorities
        assert "normal" in all_priorities
        assert "low" in all_priorities

    def test_is_valid(self):
        """Test priority validation."""
        assert BatchPriority.is_valid("high") is True
        assert BatchPriority.is_valid("normal") is True
        assert BatchPriority.is_valid("low") is True
        assert BatchPriority.is_valid("invalid") is False

    def test_to_celery_priority(self):
        """Test priority conversion to Celery priority."""
        assert BatchPriority.to_celery_priority("high") == 9
        assert BatchPriority.to_celery_priority("normal") == 5
        assert BatchPriority.to_celery_priority("low") == 1
        assert BatchPriority.to_celery_priority("unknown") == 5  # Default


class TestBatchStateManager:
    """Tests for Redis batch state manager."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def state_manager(self, mock_redis):
        """Create a BatchStateManager with mock Redis."""
        manager = BatchStateManager(redis_client=mock_redis)
        return manager

    def test_create_batch(self, state_manager, mock_redis):
        """Test creating a batch in Redis."""
        batch_id = str(uuid.uuid4())
        project_ids = ["proj-1", "proj-2", "proj-3"]

        result = state_manager.create_batch(
            batch_id=batch_id,
            project_ids=project_ids,
            concurrency=5,
            priority="high",
            name="Test Batch",
        )

        assert result["id"] == batch_id
        assert result["status"] == "pending"
        assert result["priority"] == "high"
        assert result["concurrency"] == "5"
        mock_redis.hset.assert_called_once()
        mock_redis.expire.assert_called_once()

    def test_get_batch(self, state_manager, mock_redis):
        """Test getting batch data from Redis."""
        batch_id = "test-batch-id"
        mock_redis.hgetall.return_value = {
            "id": batch_id,
            "status": "running",
            "project_ids": json.dumps(["proj-1", "proj-2"]),
            "task_ids": json.dumps(["task-1"]),
            "concurrency": "3",
            "total_projects": "2",
            "completed_projects": "1",
            "failed_projects": "0",
        }

        result = state_manager.get_batch(batch_id)

        assert result["id"] == batch_id
        assert result["status"] == "running"
        assert result["project_ids"] == ["proj-1", "proj-2"]
        assert result["task_ids"] == ["task-1"]

    def test_get_batch_not_found(self, state_manager, mock_redis):
        """Test getting non-existent batch."""
        mock_redis.hgetall.return_value = {}
        result = state_manager.get_batch("nonexistent")
        assert result is None

    def test_update_status(self, state_manager, mock_redis):
        """Test updating batch status."""
        mock_redis.exists.return_value = True

        result = state_manager.update_status(
            batch_id="test-batch",
            status="running",
            started_at="2024-01-01T00:00:00",
        )

        assert result is True
        mock_redis.hset.assert_called_once()

    def test_update_status_not_found(self, state_manager, mock_redis):
        """Test updating status for non-existent batch."""
        mock_redis.exists.return_value = False
        result = state_manager.update_status("nonexistent", "running")
        assert result is False

    def test_increment_completed(self, state_manager, mock_redis):
        """Test incrementing completed count."""
        mock_redis.hincrby.return_value = 2

        result = state_manager.increment_completed("test-batch")

        mock_redis.hincrby.assert_called_once_with(
            "batch:test-batch", "completed_projects", 1
        )
        assert result == 2

    def test_increment_failed(self, state_manager, mock_redis):
        """Test incrementing failed count."""
        mock_redis.hincrby.return_value = 1

        result = state_manager.increment_failed("test-batch")

        mock_redis.hincrby.assert_called_once_with(
            "batch:test-batch", "failed_projects", 1
        )
        assert result == 1

    def test_add_task_id(self, state_manager, mock_redis):
        """Test adding a task ID."""
        mock_redis.hget.return_value = json.dumps(["task-1"])

        result = state_manager.add_task_id("test-batch", "task-2")

        assert result is True
        mock_redis.rpush.assert_called()
        mock_redis.hset.assert_called()

    def test_get_task_ids(self, state_manager, mock_redis):
        """Test getting all task IDs."""
        mock_redis.lrange.return_value = ["task-1", "task-2", "task-3"]

        result = state_manager.get_task_ids("test-batch")

        assert result == ["task-1", "task-2", "task-3"]
        mock_redis.lrange.assert_called_once_with("batch_tasks:test-batch", 0, -1)

    def test_add_error(self, state_manager, mock_redis):
        """Test adding an error."""
        result = state_manager.add_error(
            batch_id="test-batch",
            project_id="proj-1",
            error_message="Test error",
        )

        assert result is True
        mock_redis.rpush.assert_called()

    def test_get_errors(self, state_manager, mock_redis):
        """Test getting errors."""
        mock_redis.lrange.return_value = [
            json.dumps({"project_id": "proj-1", "error": "Error 1"}),
            json.dumps({"project_id": "proj-2", "error": "Error 2"}),
        ]

        result = state_manager.get_errors("test-batch")

        assert len(result) == 2
        assert result[0]["project_id"] == "proj-1"
        assert result[1]["project_id"] == "proj-2"

    def test_delete_batch(self, state_manager, mock_redis):
        """Test deleting a batch."""
        result = state_manager.delete_batch("test-batch")

        mock_redis.delete.assert_called_once()
        assert result is True

    def test_get_progress(self, state_manager, mock_redis):
        """Test getting batch progress."""
        mock_redis.hgetall.return_value = {
            "id": "test-batch",
            "status": "running",
            "project_ids": json.dumps(["p1", "p2", "p3", "p4", "p5"]),
            "task_ids": "[]",
            "total_projects": "5",
            "completed_projects": "3",
            "failed_projects": "1",
        }

        result = state_manager.get_progress("test-batch")

        assert result["batch_id"] == "test-batch"
        assert result["status"] == "running"
        assert result["total"] == 5
        assert result["completed"] == 3
        assert result["failed"] == 1
        assert result["processed"] == 4
        assert result["remaining"] == 1
        assert result["progress_percentage"] == 80.0
        assert result["success_rate"] == 60.0

    def test_get_progress_not_found(self, state_manager, mock_redis):
        """Test getting progress for non-existent batch."""
        mock_redis.hgetall.return_value = {}

        result = state_manager.get_progress("nonexistent")

        assert "error" in result
        assert result["error"] == "Batch not found"

    def test_list_active_batches(self, state_manager, mock_redis):
        """Test listing active batches."""
        mock_redis.keys.return_value = ["batch:batch-1", "batch:batch-2", "batch:batch-3"]
        mock_redis.hgetall.side_effect = [
            {"id": "batch-1", "status": "running", "created_at": "2024-01-01T12:00:00"},
            {"id": "batch-2", "status": "completed", "created_at": "2024-01-01T11:00:00"},
            {"id": "batch-3", "status": "pending", "created_at": "2024-01-01T13:00:00"},
        ]

        result = state_manager.list_active_batches()

        # Only running and pending should be included
        assert len(result) == 2
        ids = [b["id"] for b in result]
        assert "batch-1" in ids
        assert "batch-3" in ids
        assert "batch-2" not in ids


class TestGetBatchStateManager:
    """Tests for the singleton factory function."""

    def test_singleton_returns_same_instance(self):
        """Test that get_batch_state_manager returns a singleton."""
        # Reset the singleton
        import app.services.batch_state as module
        module._batch_state_manager = None

        with patch('app.services.batch_state.redis.from_url') as mock_redis:
            mock_redis.return_value = MagicMock()

            manager1 = get_batch_state_manager()
            manager2 = get_batch_state_manager()

            assert manager1 is manager2

    def test_creates_manager_with_redis_from_settings(self):
        """Test that manager is created with Redis from settings."""
        import app.services.batch_state as module
        module._batch_state_manager = None

        with patch('app.services.batch_state.redis.from_url') as mock_redis:
            mock_redis.return_value = MagicMock()

            manager = get_batch_state_manager()

            assert manager is not None
            mock_redis.assert_called_once()
