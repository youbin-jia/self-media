# backend/app/services/batch/scheduler.py
"""
SmartScheduler for intelligent batch job scheduling based on system resources.

Key features:
- Monitors CPU, memory usage with psutil
- Dynamically adjusts concurrency based on load
- Queue management with priority support
- Integration with BatchStateManager for real-time tracking
"""
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

import psutil

from app.models.batch import BatchJob, BatchStatus, BatchPriority
from app.services.batch_state import BatchStateManager

logger = logging.getLogger(__name__)


class SmartScheduler:
    """
    Intelligent batch job scheduler that optimizes concurrency based on system resources.

    Features:
    - Real-time system monitoring (CPU, memory)
    - Dynamic concurrency adjustment
    - Priority-based scheduling
    - Integration with BatchStateManager and BatchJob model
    """

    def __init__(
        self,
        state_manager: Optional[BatchStateManager] = None,
        db_session: Optional[Any] = None,
    ):
        """
        Initialize the SmartScheduler.

        Args:
            state_manager: BatchStateManager for Redis state management
            db_session: SQLAlchemy session for database operations
        """
        self.state_manager = state_manager or BatchStateManager()
        self.db = db_session
        logger.info("SmartScheduler initialized")

    def get_system_load(self) -> Dict[str, float]:
        """
        Get current system load metrics.

        Returns:
            Dictionary with CPU percent, memory percent, and CPU count
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "cpu_count": cpu_count,
        }

    def get_recommended_concurrency(self) -> int:
        """
        Calculate recommended concurrency based on current system load.

        Uses a simple algorithm:
        - Low load (CPU < 40% and Memory < 50%): Use up to CPU cores
        - High load (CPU > 70% or Memory > 80%): Reduce to 1-2 workers
        - Moderate load: Use half of CPU cores

        Returns:
            Recommended number of concurrent tasks
        """
        load = self.get_system_load()
        cpu_percent = load["cpu_percent"]
        memory_percent = load["memory_percent"]
        cpu_count = load["cpu_count"]

        # High load scenario - reduce concurrency
        if cpu_percent > 70.0 or memory_percent > 80.0:
            recommended = max(1, cpu_count // 4)
            logger.debug(
                f"High load detected (CPU: {cpu_percent}%, Mem: {memory_percent}%), "
                f"recommending {recommended} concurrent tasks"
            )
            return recommended

        # Low load scenario - maximize concurrency
        if cpu_percent < 40.0 and memory_percent < 50.0:
            recommended = cpu_count
            logger.debug(
                f"Low load detected (CPU: {cpu_percent}%, Mem: {memory_percent}%), "
                f"recommending {recommended} concurrent tasks"
            )
            return recommended

        # Moderate load - use half of CPU cores
        recommended = max(2, cpu_count // 2)
        logger.debug(
            f"Moderate load detected (CPU: {cpu_percent}%, Mem: {memory_percent}%), "
            f"recommending {recommended} concurrent tasks"
        )
        return recommended

    def schedule_batch(
        self,
        project_ids: List[str],
        priority: str = "normal",
        concurrency: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Schedule a batch job with intelligent concurrency management.

        Args:
            project_ids: List of project IDs to process
            priority: Batch priority (high, normal, low)
            concurrency: Optional explicit concurrency override
            name: Optional batch name

        Returns:
            Dictionary with batch_id, status, and concurrency

        Raises:
            ValueError: If priority is invalid or project_ids is empty
        """
        # Validate inputs
        if not project_ids:
            raise ValueError("project_ids cannot be empty")

        if not BatchPriority.is_valid(priority):
            raise ValueError(f"Invalid priority: {priority}")

        # Determine concurrency
        if concurrency is None:
            concurrency = self.get_recommended_concurrency()
        else:
            # Ensure user-provided concurrency is within reasonable bounds
            cpu_count = psutil.cpu_count()
            concurrency = max(1, min(concurrency, cpu_count))

        # Generate batch ID
        batch_id = str(uuid.uuid4())

        logger.info(
            f"Scheduling batch {batch_id} with {len(project_ids)} projects, "
            f"priority={priority}, concurrency={concurrency}"
        )

        # Create batch in Redis state manager
        batch_data = self.state_manager.create_batch(
            batch_id=batch_id,
            project_ids=project_ids,
            concurrency=concurrency,
            priority=priority,
            name=name,
        )

        # Create BatchJob in database if db session is available
        if self.db:
            try:
                batch_job = BatchJob(
                    id=batch_id,
                    name=name,
                    project_ids=project_ids,
                    total_projects=len(project_ids),
                    priority=priority,
                    concurrency=concurrency,
                    status=BatchStatus.QUEUED,
                )
                self.db.add(batch_job)
                self.db.commit()
                logger.debug(f"BatchJob {batch_id} persisted to database")
            except Exception as e:
                logger.error(f"Failed to persist BatchJob to database: {e}")
                # Continue even if database persistence fails

        return {
            "batch_id": batch_id,
            "status": "queued",
            "concurrency": concurrency,
            "priority": priority,
            "total_projects": len(project_ids),
        }

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current batch queue.

        Returns:
            Dictionary with queue statistics including counts by status and priority
        """
        active_batches = self.state_manager.list_active_batches()

        stats = {
            "total_active": len(active_batches),
            "queued": 0,
            "running": 0,
            "by_priority": {
                "high": 0,
                "normal": 0,
                "low": 0,
            },
        }

        for batch in active_batches:
            status = batch.get("status", "unknown")
            priority = batch.get("priority", "normal")

            if status == "queued":
                stats["queued"] += 1
            elif status == "running":
                stats["running"] += 1

            if priority in stats["by_priority"]:
                stats["by_priority"][priority] += 1

        return stats

    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scheduler status including system load and recommendations.

        Returns:
            Dictionary with system load, recommended concurrency, and queue stats
        """
        system_load = self.get_system_load()
        recommended_concurrency = self.get_recommended_concurrency()
        queue_stats = self.get_queue_stats()

        return {
            "system_load": system_load,
            "recommended_concurrency": recommended_concurrency,
            "queue_stats": queue_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
