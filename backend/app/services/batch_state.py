# backend/app/services/batch_state.py
"""
Redis state management for batch processing.

Provides real-time tracking of batch jobs with Redis for:
- Fast status updates
- Progress tracking
- Task ID management
- Distributed state synchronization
"""
import json
import logging
import redis
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.config import settings
from app.models.batch import BatchStatus, BatchPriority

logger = logging.getLogger(__name__)


class BatchStateManager:
    """
    Redis-based state manager for batch jobs.

    Key features:
    - Real-time state updates
    - Atomic operations for consistency
    - TTL for automatic cleanup
    - Support for distributed processing
    """

    # Redis key prefixes
    BATCH_KEY_PREFIX = "batch:"
    BATCH_TASKS_KEY_PREFIX = "batch_tasks:"
    BATCH_ERRORS_KEY_PREFIX = "batch_errors:"

    # Default TTL for batch data (7 days)
    DEFAULT_TTL = 60 * 60 * 24 * 7

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize the batch state manager.

        Args:
            redis_client: Optional Redis client. If not provided, creates one from settings.
        """
        if redis_client:
            self.redis = redis_client
        else:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def create_batch(
        self,
        batch_id: str,
        project_ids: List[str],
        concurrency: int = 3,
        priority: str = "normal",
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new batch job in Redis.

        Args:
            batch_id: Unique batch identifier (UUID)
            project_ids: List of project UUIDs to process
            concurrency: Number of parallel tasks
            priority: Batch priority (high, normal, low)
            name: Optional user-friendly name

        Returns:
            Dictionary with batch data

        Raises:
            ValueError: If priority or status is invalid
            redis.RedisError: If Redis operation fails
        """
        # Validate priority
        if not BatchPriority.is_valid(priority):
            raise ValueError(f"Invalid priority: {priority}")

        logger.info(f"Creating batch {batch_id} with {len(project_ids)} projects")

        now = datetime.utcnow().isoformat()

        batch_data = {
            "id": batch_id,
            "name": name or "",
            "project_ids": json.dumps(project_ids),
            "task_ids": json.dumps([]),
            "status": "queued",
            "priority": priority,
            "concurrency": str(concurrency),
            "total_projects": str(len(project_ids)),
            "completed_projects": "0",
            "failed_projects": "0",
            "created_at": now,
            "started_at": "",
            "completed_at": "",
        }

        try:
            # Store batch data using hash
            key = f"{self.BATCH_KEY_PREFIX}{batch_id}"
            self.redis.hset(key, mapping=batch_data)
            self.redis.expire(key, self.DEFAULT_TTL)
            logger.debug(f"Batch {batch_id} created successfully")
            return batch_data
        except redis.RedisError as e:
            logger.error(f"Failed to create batch {batch_id}: {e}")
            raise

    def get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get batch data from Redis.

        Args:
            batch_id: Batch identifier

        Returns:
            Dictionary with batch data or None if not found
        """
        key = f"{self.BATCH_KEY_PREFIX}{batch_id}"
        data = self.redis.hgetall(key)

        if not data:
            return None

        # Decode JSON fields
        result = dict(data)
        if "project_ids" in result:
            result["project_ids"] = json.loads(result["project_ids"])
        if "task_ids" in result:
            result["task_ids"] = json.loads(result["task_ids"])

        return result

    def update_status(
        self,
        batch_id: str,
        status: str,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> bool:
        """
        Update batch status.

        Args:
            batch_id: Batch identifier
            status: New status (queued, running, completed, failed, cancelled)
            started_at: Optional started timestamp
            completed_at: Optional completed timestamp

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If status is invalid
            redis.RedisError: If Redis operation fails
        """
        # Validate status
        if not BatchStatus.is_valid(status):
            raise ValueError(f"Invalid status: {status}")

        key = f"{self.BATCH_KEY_PREFIX}{batch_id}"

        try:
            if not self.redis.exists(key):
                logger.warning(f"Batch {batch_id} not found for status update")
                return False

            updates = {"status": status}
            if started_at:
                updates["started_at"] = started_at
            if completed_at:
                updates["completed_at"] = completed_at

            self.redis.hset(key, mapping=updates)
            logger.info(f"Batch {batch_id} status updated to {status}")
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to update batch {batch_id} status: {e}")
            raise

    def increment_completed(self, batch_id: str) -> int:
        """
        Atomically increment completed projects count.

        Args:
            batch_id: Batch identifier

        Returns:
            New completed count

        Raises:
            redis.RedisError: If Redis operation fails
        """
        try:
            key = f"{self.BATCH_KEY_PREFIX}{batch_id}"
            result = self.redis.hincrby(key, "completed_projects", 1)
            logger.debug(f"Batch {batch_id} completed count incremented to {result}")
            return result
        except redis.RedisError as e:
            logger.error(f"Failed to increment completed count for batch {batch_id}: {e}")
            raise

    def increment_failed(self, batch_id: str) -> int:
        """
        Atomically increment failed projects count.

        Args:
            batch_id: Batch identifier

        Returns:
            New failed count

        Raises:
            redis.RedisError: If Redis operation fails
        """
        try:
            key = f"{self.BATCH_KEY_PREFIX}{batch_id}"
            result = self.redis.hincrby(key, "failed_projects", 1)
            logger.debug(f"Batch {batch_id} failed count incremented to {result}")
            return result
        except redis.RedisError as e:
            logger.error(f"Failed to increment failed count for batch {batch_id}: {e}")
            raise

    def add_task_id(self, batch_id: str, task_id: str) -> bool:
        """
        Add a Celery task ID to the batch.

        Args:
            batch_id: Batch identifier
            task_id: Celery task ID

        Returns:
            True if successful

        Raises:
            redis.RedisError: If Redis operation fails
        """
        try:
            # Add to task list
            list_key = f"{self.BATCH_TASKS_KEY_PREFIX}{batch_id}"
            self.redis.rpush(list_key, task_id)
            self.redis.expire(list_key, self.DEFAULT_TTL)

            # Also update in batch hash
            key = f"{self.BATCH_KEY_PREFIX}{batch_id}"
            current_tasks = self.redis.hget(key, "task_ids")
            tasks = json.loads(current_tasks) if current_tasks else []
            tasks.append(task_id)
            self.redis.hset(key, "task_ids", json.dumps(tasks))

            logger.debug(f"Task {task_id} added to batch {batch_id}")
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to add task {task_id} to batch {batch_id}: {e}")
            raise

    def get_task_ids(self, batch_id: str) -> List[str]:
        """
        Get all Celery task IDs for a batch.

        Args:
            batch_id: Batch identifier

        Returns:
            List of task IDs
        """
        list_key = f"{self.BATCH_TASKS_KEY_PREFIX}{batch_id}"
        return self.redis.lrange(list_key, 0, -1)

    def add_error(
        self,
        batch_id: str,
        project_id: str,
        error_message: str,
    ) -> bool:
        """
        Record an error for a project in the batch.

        Args:
            batch_id: Batch identifier
            project_id: Project that failed
            error_message: Error description

        Returns:
            True if successful

        Raises:
            redis.RedisError: If Redis operation fails
        """
        error_entry = {
            "project_id": project_id,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Add to error list
            errors_key = f"{self.BATCH_ERRORS_KEY_PREFIX}{batch_id}"
            self.redis.rpush(errors_key, json.dumps(error_entry))
            self.redis.expire(errors_key, self.DEFAULT_TTL)

            logger.warning(f"Error recorded for project {project_id} in batch {batch_id}: {error_message}")
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to add error for batch {batch_id}: {e}")
            raise

    def get_errors(self, batch_id: str) -> List[Dict[str, Any]]:
        """
        Get all errors for a batch.

        Args:
            batch_id: Batch identifier

        Returns:
            List of error entries
        """
        errors_key = f"{self.BATCH_ERRORS_KEY_PREFIX}{batch_id}"
        errors = self.redis.lrange(errors_key, 0, -1)
        return [json.loads(e) for e in errors]

    def delete_batch(self, batch_id: str) -> bool:
        """
        Delete all batch-related data from Redis.

        Args:
            batch_id: Batch identifier

        Returns:
            True if successful
        """
        keys_to_delete = [
            f"{self.BATCH_KEY_PREFIX}{batch_id}",
            f"{self.BATCH_TASKS_KEY_PREFIX}{batch_id}",
            f"{self.BATCH_ERRORS_KEY_PREFIX}{batch_id}",
        ]

        self.redis.delete(*keys_to_delete)
        return True

    def get_progress(self, batch_id: str) -> Dict[str, Any]:
        """
        Get real-time progress for a batch.

        Args:
            batch_id: Batch identifier

        Returns:
            Dictionary with progress information
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return {"error": "Batch not found"}

        total = int(batch.get("total_projects", 0))
        completed = int(batch.get("completed_projects", 0))
        failed = int(batch.get("failed_projects", 0))
        processed = completed + failed

        progress = {
            "batch_id": batch_id,
            "status": batch.get("status"),
            "total": total,
            "completed": completed,
            "failed": failed,
            "processed": processed,
            "remaining": total - processed,
            "progress_percentage": round((processed / total * 100) if total > 0 else 0, 1),
            "success_rate": round((completed / total * 100) if total > 0 else 0, 1),
        }

        return progress

    def list_active_batches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List all active (queued or running) batches.

        Args:
            limit: Maximum number of batches to return

        Returns:
            List of batch data dictionaries
        """
        pattern = f"{self.BATCH_KEY_PREFIX}*"
        batch_keys = self.redis.keys(pattern)[:limit]

        batches = []
        for key in batch_keys:
            batch_id = key.replace(self.BATCH_KEY_PREFIX, "")
            batch = self.get_batch(batch_id)
            if batch and batch.get("status") in ("queued", "running"):
                batches.append(batch)

        # Sort by created_at descending
        batches.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return batches


# Singleton instance
_batch_state_manager: Optional[BatchStateManager] = None


def get_batch_state_manager() -> BatchStateManager:
    """Get or create the singleton BatchStateManager instance."""
    global _batch_state_manager
    if _batch_state_manager is None:
        _batch_state_manager = BatchStateManager()
    return _batch_state_manager
