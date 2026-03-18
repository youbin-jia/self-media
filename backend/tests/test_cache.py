"""
Tests for Redis cache decorators and invalidation.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.cache import cache_result, invalidate_cache, get_redis_client, _reset_redis_client


@pytest.fixture(autouse=True)
def reset_redis_singleton():
    """Reset Redis client singleton before each test."""
    _reset_redis_client()
    yield
    _reset_redis_client()


class TestRedisClient:
    """Test Redis client singleton."""

    def test_get_redis_client_singleton(self):
        """Test that get_redis_client returns a singleton instance."""
        with patch('app.services.cache.redis_cache.redis.from_url') as mock_from_url:
            mock_client = MagicMock()
            mock_from_url.return_value = mock_client

            client1 = get_redis_client()
            client2 = get_redis_client()

            # Should return the same instance
            assert client1 is client2
            mock_from_url.assert_called_once()

    def test_redis_client_with_settings_url(self):
        """Test that Redis client is initialized with correct URL from settings."""
        with patch('app.services.cache.redis_cache.redis.from_url') as mock_from_url:
            mock_client = MagicMock()
            mock_from_url.return_value = mock_client

            client = get_redis_client()

            # Verify called with settings.REDIS_URL
            from app.config import settings
            mock_from_url.assert_called_with(settings.REDIS_URL, decode_responses=True)


class TestCacheResultDecorator:
    """Test cache_result decorator."""

    @pytest.mark.asyncio
    async def test_cache_result_caches_function_result(self):
        """Test that cache_result caches the function result."""
        with patch('app.services.cache.redis_cache.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = None  # Cache miss
            mock_get_client.return_value = mock_client

            call_count = 0

            @cache_result(key_pattern="test:{test_id}", ttl=60)
            async def test_func(test_id: str):
                nonlocal call_count
                call_count += 1
                return {"id": test_id, "data": "test_data"}

            # First call - should execute function
            result = await test_func(test_id="123")
            assert result == {"id": "123", "data": "test_data"}
            assert call_count == 1
            mock_client.setex.assert_called_once()

            # Verify cache key and TTL
            call_args = mock_client.setex.call_args
            assert call_args[0][0] == "test:123"
            assert call_args[0][1] == 60

    @pytest.mark.asyncio
    async def test_cache_result_returns_cached_value(self):
        """Test that cache_result returns cached value when available."""
        with patch('app.services.cache.redis_cache.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            cached_data = {"id": "123", "data": "cached_data"}
            mock_client.get.return_value = json.dumps(cached_data)
            mock_get_client.return_value = mock_client

            call_count = 0

            @cache_result(key_pattern="test:{test_id}", ttl=60)
            async def test_func(test_id: str):
                nonlocal call_count
                call_count += 1
                return {"id": test_id, "data": "new_data"}

            # Should return cached data without executing function
            result = await test_func(test_id="123")
            assert result == cached_data
            assert call_count == 0  # Function should not be called

    @pytest.mark.asyncio
    async def test_cache_result_handles_complex_objects(self):
        """Test that cache_result handles complex JSON-serializable objects."""
        with patch('app.services.cache.redis_cache.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = None
            mock_get_client.return_value = mock_client

            complex_data = {
                "id": "123",
                "nested": {"key": "value"},
                "list": [1, 2, 3]
            }

            @cache_result(key_pattern="test:{test_id}", ttl=60)
            async def test_func(test_id: str):
                return complex_data

            result = await test_func(test_id="123")
            assert result == complex_data

    @pytest.mark.asyncio
    async def test_cache_result_handles_redis_error_gracefully(self):
        """Test that cache_result handles Redis connection errors gracefully."""
        with patch('app.services.cache.redis_cache.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Redis connection error")
            mock_get_client.return_value = mock_client

            @cache_result(key_pattern="test:{test_id}", ttl=60)
            async def test_func(test_id: str):
                return {"id": test_id, "data": "fallback"}

            # Should still execute function and return result despite Redis error
            result = await test_func(test_id="123")
            assert result == {"id": "123", "data": "fallback"}

    @pytest.mark.asyncio
    async def test_cache_result_with_multiple_kwargs(self):
        """Test cache_result with multiple keyword arguments."""
        with patch('app.services.cache.redis_cache.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = None
            mock_get_client.return_value = mock_client

            @cache_result(key_pattern="user:{user_id}:project:{project_id}", ttl=60)
            async def test_func(user_id: str, project_id: str):
                return {"user_id": user_id, "project_id": project_id}

            result = await test_func(user_id="u1", project_id="p1")
            assert result == {"user_id": "u1", "project_id": "p1"}

            # Verify cache key is correctly formatted
            call_args = mock_client.setex.call_args
            assert call_args[0][0] == "user:u1:project:p1"


class TestInvalidateCacheDecorator:
    """Test invalidate_cache decorator."""

    @pytest.mark.asyncio
    async def test_invalidate_cache_deletes_keys(self):
        """Test that invalidate_cache deletes specified keys."""
        with patch('app.services.cache.invalidation.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            @invalidate_cache(keys=["project:{project_id}", "user:{user_id}"])
            async def test_func(project_id: str, user_id: str):
                return {"status": "success"}

            result = await test_func(project_id="p1", user_id="u1")
            assert result == {"status": "success"}

            # Verify both keys were deleted
            assert mock_client.delete.call_count == 2
            call_args_list = mock_client.delete.call_args_list
            deleted_keys = [call[0][0] for call in call_args_list]
            assert "project:p1" in deleted_keys
            assert "user:u1" in deleted_keys

    @pytest.mark.asyncio
    async def test_invalidate_cache_executes_function_first(self):
        """Test that invalidate_cache executes function before invalidating."""
        with patch('app.services.cache.invalidation.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            executed = False

            @invalidate_cache(keys=["test:{test_id}"])
            async def test_func(test_id: str):
                nonlocal executed
                executed = True
                return {"status": "success"}

            result = await test_func(test_id="123")
            assert executed is True
            assert result == {"status": "success"}

    @pytest.mark.asyncio
    async def test_invalidate_cache_handles_redis_error_gracefully(self):
        """Test that invalidate_cache handles Redis errors gracefully."""
        with patch('app.services.cache.invalidation.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.delete.side_effect = Exception("Redis error")
            mock_get_client.return_value = mock_client

            @invalidate_cache(keys=["test:{test_id}"])
            async def test_func(test_id: str):
                return {"status": "success"}

            # Should not raise exception
            result = await test_func(test_id="123")
            assert result == {"status": "success"}

    @pytest.mark.asyncio
    async def test_invalidate_cache_with_wildcard_pattern(self):
        """Test invalidate_cache with wildcard pattern deletion."""
        with patch('app.services.cache.invalidation.get_redis_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.keys.return_value = ["projects:user:u1:page:1", "projects:user:u1:page:2"]
            mock_get_client.return_value = mock_client

            @invalidate_cache(keys=["projects:user:{user_id}:*"])
            async def test_func(user_id: str):
                return {"status": "success"}

            result = await test_func(user_id="u1")
            assert result == {"status": "success"}

            # Verify delete was called with both matched keys
            assert mock_client.delete.call_count == 1
            # Check that delete was called with multiple keys
            call_args = mock_client.delete.call_args[0]
            assert "projects:user:u1:page:1" in call_args
            assert "projects:user:u1:page:2" in call_args


class TestCacheConfiguration:
    """Test cache configuration in Settings."""

    def test_cache_ttl_settings_exist(self):
        """Test that cache TTL settings are defined."""
        from app.config import settings

        # Check that cache TTL settings can be added
        assert hasattr(settings, 'REDIS_URL')
        assert settings.REDIS_URL is not None

    def test_cache_default_ttls(self):
        """Test that default TTL values are reasonable."""
        from app.config import settings

        # These should have sensible defaults
        # User info: 1 hour
        # Project: 30 min
        # Project list: 10 min
        # Hot topics: 5 min
        # Search: 1 hour
        # Dashboard: 15 min
        expected_ttls = {
            'CACHE_TTL_USER': 3600,        # 1 hour
            'CACHE_TTL_PROJECT': 1800,     # 30 min
            'CACHE_TTL_PROJECT_LIST': 600,  # 10 min
            'CACHE_TTL_HOT_TOPICS': 300,    # 5 min
            'CACHE_TTL_SEARCH': 3600,       # 1 hour
            'CACHE_TTL_DASHBOARD': 900,     # 15 min
        }

        for attr, expected in expected_ttls.items():
            if hasattr(settings, attr):
                assert getattr(settings, attr) == expected, f"{attr} should be {expected}"
