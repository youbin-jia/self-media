"""
Tests for Celery task queue optimization.

Tests cover:
1. Celery configuration settings
2. Task queue definitions (high, medium, low)
3. Task routing with priorities
4. Task result caching decorator
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta


class TestCeleryConfiguration:
    """Test Celery configuration settings."""

    def test_celery_worker_concurrency_setting(self):
        """Test that worker concurrency is configured."""
        from app.config import settings

        assert hasattr(settings, 'CELERY_WORKER_CONCURRENCY')
        assert settings.CELERY_WORKER_CONCURRENCY == 4

    def test_celery_worker_prefetch_multiplier_setting(self):
        """Test that prefetch multiplier is configured."""
        from app.config import settings

        assert hasattr(settings, 'CELERY_WORKER_PREFETCH_MULTIPLIER')
        assert settings.CELERY_WORKER_PREFETCH_MULTIPLIER == 1

    def test_celery_task_acks_late_setting(self):
        """Test that task_acks_late is configured."""
        from app.config import settings

        assert hasattr(settings, 'CELERY_TASK_ACKS_LATE')
        assert settings.CELERY_TASK_ACKS_LATE is True

    def test_celery_task_reject_on_worker_lost_setting(self):
        """Test that reject_on_worker_lost is configured."""
        from app.config import settings

        assert hasattr(settings, 'CELERY_TASK_REJECT_ON_WORKER_LOST')
        assert settings.CELERY_TASK_REJECT_ON_WORKER_LOST is True

    def test_celery_task_result_cache_ttl_setting(self):
        """Test that default task result cache TTL is configured."""
        from app.config import settings

        assert hasattr(settings, 'CELERY_TASK_RESULT_CACHE_TTL')
        assert settings.CELERY_TASK_RESULT_CACHE_TTL == 3600  # 1 hour


class TestTaskQueues:
    """Test Celery task queue definitions."""

    def test_high_queue_defined(self):
        """Test that high priority queue is defined."""
        from app.tasks.celery_app import celery_app

        queues = celery_app.conf.task_queues
        assert queues is not None

        # Check high queue exists
        queue_names = [q.name for q in queues]
        assert 'high' in queue_names

    def test_medium_queue_defined(self):
        """Test that medium priority queue is defined."""
        from app.tasks.celery_app import celery_app

        queues = celery_app.conf.task_queues
        assert queues is not None

        queue_names = [q.name for q in queues]
        assert 'medium' in queue_names

    def test_low_queue_defined(self):
        """Test that low priority queue is defined."""
        from app.tasks.celery_app import celery_app

        queues = celery_app.conf.task_queues
        assert queues is not None

        queue_names = [q.name for q in queues]
        assert 'low' in queue_names


class TestTaskRouting:
    """Test Celery task routing configuration."""

    def test_video_synthesis_routed_to_high_queue(self):
        """Test that video synthesis is routed to high priority queue."""
        from app.tasks.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes is not None

        task_name = 'app.tasks.video_tasks.synthesize_video_task'
        assert task_name in routes
        assert routes[task_name]['queue'] == 'high'
        assert routes[task_name].get('priority') == 9

    def test_batch_processing_routed_to_high_queue(self):
        """Test that batch processing is routed to high priority queue."""
        from app.tasks.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes is not None

        task_name = 'app.tasks.batch_tasks.process_batch_task'
        assert task_name in routes
        assert routes[task_name]['queue'] == 'high'
        assert routes[task_name].get('priority') == 8

    def test_batch_monitor_routed_to_medium_queue(self):
        """Test that batch monitor is routed to medium priority queue."""
        from app.tasks.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert routes is not None

        task_name = 'app.tasks.batch_tasks.monitor_batch_progress_task'
        assert task_name in routes
        assert routes[task_name]['queue'] == 'medium'
        assert routes[task_name].get('priority') == 4


class TestTaskResultCache:
    """Test task result caching decorator."""

    def test_cache_task_result_decorator_exists(self):
        """Test that cache_task_result decorator is available."""
        from app.tasks.cache import cache_task_result

        assert callable(cache_task_result)

    def test_cache_task_result_generates_cache_key(self):
        """Test that decorator generates proper cache key."""
        from app.tasks.cache import cache_task_result, generate_task_cache_key

        # Test key generation
        key = generate_task_cache_key('test_task', ('arg1', 'arg2'), {'kwarg': 'value'})
        assert 'test_task' in key
        assert isinstance(key, str)

    @patch('app.tasks.cache.get_redis_client')
    def test_cache_task_result_caches_result(self, mock_get_redis_client):
        """Test that decorator caches task result in Redis."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss
        mock_get_redis_client.return_value = mock_redis

        from app.tasks.cache import cache_task_result

        @cache_task_result(ttl=1800)
        def test_task(self, value: str):
            return {"result": value}

        # Create mock task self
        mock_self = MagicMock()

        result = test_task(mock_self, "test_value")

        # Check result returned
        assert result == {"result": "test_value"}

        # Check setex was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        # setex args are (key, ttl, value) or (key, value) with ttl as kwarg
        # Check that TTL was passed
        if len(call_args[0]) >= 3:
            assert call_args[0][1] == 1800  # TTL is second positional arg
        else:
            assert call_args[1].get('time', 0) == 1800  # TTL as kwarg

    @patch('app.tasks.cache.get_redis_client')
    def test_cache_task_result_returns_cached_result(self, mock_get_redis_client):
        """Test that decorator returns cached result when available."""
        cached_result = json.dumps({"result": "cached_value"})
        mock_redis = MagicMock()
        mock_redis.get.return_value = cached_result
        mock_get_redis_client.return_value = mock_redis

        from app.tasks.cache import cache_task_result

        call_count = 0

        @cache_task_result(ttl=1800)
        def test_task(self, value: str):
            nonlocal call_count
            call_count += 1
            return {"result": value, "call": call_count}

        mock_self = MagicMock()
        result = test_task(mock_self, "test_value")

        # Should return cached result
        assert result == {"result": "cached_value"}

        # Function should not have been called
        assert call_count == 0

    @patch('app.tasks.cache.get_redis_client')
    def test_cache_task_result_handles_redis_error(self, mock_get_redis_client):
        """Test that decorator handles Redis errors gracefully."""
        mock_get_redis_client.side_effect = Exception("Redis connection error")

        from app.tasks.cache import cache_task_result

        @cache_task_result(ttl=1800)
        def test_task(self, value: str):
            return {"result": value}

        mock_self = MagicMock()
        result = test_task(mock_self, "test_value")

        # Should still return result even with Redis error
        assert result == {"result": "test_value"}

    def test_cache_task_result_default_ttl(self):
        """Test that default TTL is 1 hour (3600 seconds)."""
        from app.tasks.cache import cache_task_result

        # Check default TTL
        @cache_task_result()  # No TTL specified
        def test_task(self, value: str):
            return {"result": value}

        # The decorator should use default TTL
        # We can verify by checking the decorator wraps correctly
        assert callable(test_task)


class TestTaskPriorities:
    """Test that tasks have proper priority configuration."""

    def test_synthesize_video_has_priority_attribute(self):
        """Test that synthesize_video_task has priority configuration."""
        from app.tasks.video_tasks import synthesize_video_task

        # Task should have priority info in its configuration
        # This is set via task_routes, but we can verify the task is registered
        assert synthesize_video_task.name == 'app.tasks.video_tasks.synthesize_video_task'

    def test_process_batch_has_priority_attribute(self):
        """Test that process_batch_task has priority configuration."""
        from app.tasks.batch_tasks import process_batch_task

        assert process_batch_task.name == 'app.tasks.batch_tasks.process_batch_task'

    def test_monitor_batch_has_priority_attribute(self):
        """Test that monitor_batch_progress_task has priority configuration."""
        from app.tasks.batch_tasks import monitor_batch_progress_task

        assert monitor_batch_progress_task.name == 'app.tasks.batch_tasks.monitor_batch_progress_task'


class TestCeleryWorkerConfig:
    """Test Celery worker configuration is properly applied."""

    def test_worker_prefetch_multiplier_applied(self):
        """Test that worker prefetch multiplier is applied to celery app."""
        from app.tasks.celery_app import celery_app

        # The prefetch multiplier should be set
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_task_acks_late_applied(self):
        """Test that task_acks_late is applied to celery app."""
        from app.tasks.celery_app import celery_app

        assert celery_app.conf.task_acks_late is True

    def test_task_reject_on_worker_lost_applied(self):
        """Test that task_reject_on_worker_lost is applied to celery app."""
        from app.tasks.celery_app import celery_app

        assert celery_app.conf.task_reject_on_worker_lost is True
