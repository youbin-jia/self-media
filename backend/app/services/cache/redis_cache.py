"""
Redis cache decorator for caching function results.
"""
import json
import redis
from functools import wraps
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client singleton.

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            logger.info(f"Redis client initialized with URL: {settings.REDIS_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise

    return _redis_client


def _reset_redis_client():
    """
    Reset the Redis client singleton (for testing purposes).
    """
    global _redis_client
    _redis_client = None


def cache_result(key_pattern: str, ttl: int = 1800):
    """
    Decorator to cache function results in Redis.

    Args:
        key_pattern: Pattern for cache key, can include {param} placeholders
        ttl: Time-to-live in seconds (default: 30 minutes)

    Returns:
        Decorated function

    Example:
        @cache_result(key_pattern="project:{project_id}", ttl=1800)
        async def get_project(project_id: str):
            return {"id": project_id, "name": "Test"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Generate cache key from pattern
                try:
                    cache_key = key_pattern.format(**kwargs)
                except KeyError as e:
                    logger.warning(
                        f"Missing parameter {e} for key pattern '{key_pattern}'. "
                        f"Available kwargs: {list(kwargs.keys())}"
                    )
                    # Fall back to executing function without caching
                    return await func(*args, **kwargs)

                # Try to get from cache
                client = get_redis_client()
                cached = client.get(cache_key)

                if cached is not None:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return json.loads(cached)

                logger.debug(f"Cache miss for key: {cache_key}")

                # Execute function
                result = await func(*args, **kwargs)

                # Store in cache
                try:
                    client.setex(cache_key, ttl, json.dumps(result))
                    logger.debug(f"Cached result for key: {cache_key}, TTL: {ttl}s")
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to cache result: {e}")

                return result

            except Exception as e:
                # Handle Redis errors gracefully - execute function without caching
                logger.error(f"Redis error in cache_result: {e}")
                return await func(*args, **kwargs)

        return wrapper
    return decorator
