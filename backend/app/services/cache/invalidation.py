"""
Cache invalidation decorator for clearing cache entries.
"""
import logging
from functools import wraps
from typing import List

from app.services.cache.redis_cache import get_redis_client

logger = logging.getLogger(__name__)


def invalidate_cache(keys: List[str]):
    """
    Decorator to invalidate cache keys after function execution.

    Args:
        keys: List of cache key patterns, can include {param} placeholders

    Returns:
        Decorated function

    Example:
        @invalidate_cache(keys=["project:{project_id}", "user:{owner_id}"])
        async def update_project(project_id: str, owner_id: str):
            return {"status": "updated"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)

            try:
                client = get_redis_client()

                # Delete each cache key
                for key_pattern in keys:
                    try:
                        # Generate actual key from pattern
                        cache_key = key_pattern.format(**kwargs)

                        # Check if key contains wildcard
                        if '*' in cache_key:
                            # Find all matching keys
                            matched_keys = client.keys(cache_key)
                            if matched_keys:
                                # Delete all matched keys
                                client.delete(*matched_keys)
                                logger.debug(
                                    f"Deleted {len(matched_keys)} keys matching pattern: {cache_key}"
                                )
                        else:
                            # Delete single key
                            deleted = client.delete(cache_key)
                            if deleted:
                                logger.debug(f"Invalidated cache key: {cache_key}")
                    except KeyError as e:
                        logger.warning(
                            f"Failed to format cache key pattern '{key_pattern}': "
                            f"missing parameter {e}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error invalidating cache key '{key_pattern}': {e}"
                        )

            except Exception as e:
                # Handle Redis errors gracefully
                logger.error(f"Redis error in invalidate_cache: {e}")

            return result

        return wrapper
    return decorator
