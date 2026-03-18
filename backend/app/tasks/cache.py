"""
Task result caching utilities for Celery tasks.

Provides a decorator to cache task results in Redis with configurable TTL.
"""
import json
import hashlib
import logging
from functools import wraps
from typing import Optional, Any, Dict

from app.config import settings
from app.services.cache.redis_cache import get_redis_client

logger = logging.getLogger(__name__)


def generate_task_cache_key(task_name: str, args: tuple, kwargs: dict) -> str:
    """
    Generate a cache key for a task result.

    Args:
        task_name: Name of the Celery task
        args: Positional arguments passed to the task
        kwargs: Keyword arguments passed to the task

    Returns:
        A unique cache key string
    """
    # Create a hash of the arguments for uniqueness
    args_str = json.dumps(args, sort_keys=True, default=str) if args else ""
    kwargs_str = json.dumps(kwargs, sort_keys=True, default=str) if kwargs else ""
    combined = f"{args_str}:{kwargs_str}"

    # Use MD5 for short, consistent hash
    args_hash = hashlib.md5(combined.encode()).hexdigest()[:12]

    return f"task_result:{task_name}:{args_hash}"


def cache_task_result(ttl: Optional[int] = None):
    """
    Decorator to cache Celery task results in Redis.

    Args:
        ttl: Time-to-live in seconds (default: from settings.CELERY_TASK_RESULT_CACHE_TTL)

    Returns:
        Decorated function that caches results

    Example:
        @celery_app.task(bind=True)
        @cache_task_result(ttl=1800)
        def process_material(self, material_id: str):
            # Process material...
            return result
    """
    if ttl is None:
        ttl = settings.CELERY_TASK_RESULT_CACHE_TTL

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            task_name = func.__name__
            cache_key = generate_task_cache_key(task_name, args, kwargs)

            try:
                # Try to get cached result
                redis_client = get_redis_client()
                cached = redis_client.get(cache_key)

                if cached is not None:
                    logger.debug(f"Task cache hit for key: {cache_key}")
                    return json.loads(cached)

                logger.debug(f"Task cache miss for key: {cache_key}")

                # Execute task
                result = func(self, *args, **kwargs)

                # Cache result
                try:
                    redis_client.setex(cache_key, ttl, json.dumps(result, default=str))
                    logger.debug(f"Cached task result for key: {cache_key}, TTL: {ttl}s")
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to cache task result: {e}")

                return result

            except Exception as e:
                # Handle Redis errors gracefully - execute task without caching
                logger.error(f"Redis error in cache_task_result: {e}")
                return func(self, *args, **kwargs)

        return wrapper

    return decorator


def invalidate_task_cache(task_name: str, args: tuple = None, kwargs: dict = None) -> bool:
    """
    Invalidate a cached task result.

    Args:
        task_name: Name of the task
        args: Positional arguments (optional, for specific cache entry)
        kwargs: Keyword arguments (optional, for specific cache entry)

    Returns:
        True if cache was invalidated, False otherwise
    """
    try:
        redis_client = get_redis_client()

        if args is None and kwargs is None:
            # Invalidate all cached results for this task
            pattern = f"task_result:{task_name}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} cache entries for task: {task_name}")
                return True
        else:
            # Invalidate specific cache entry
            cache_key = generate_task_cache_key(task_name, args or (), kwargs or {})
            if redis_client.delete(cache_key):
                logger.debug(f"Invalidated cache for key: {cache_key}")
                return True

        return False

    except Exception as e:
        logger.error(f"Failed to invalidate task cache: {e}")
        return False


def get_task_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about cached task results.

    Returns:
        Dictionary with cache statistics
    """
    try:
        redis_client = get_redis_client()
        pattern = "task_result:*"
        keys = redis_client.keys(pattern)

        stats = {
            "total_cached_tasks": len(keys),
            "keys": keys[:100] if keys else [],  # Limit to 100 for performance
        }

        return stats

    except Exception as e:
        logger.error(f"Failed to get task cache stats: {e}")
        return {"total_cached_tasks": 0, "keys": [], "error": str(e)}
