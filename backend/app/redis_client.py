"""
Redis client configuration and utilities for caching.
"""

import redis
import json
import logging
from typing import Optional, Any, Union
from datetime import timedelta

from app.config import settings

logger = logging.getLogger(__name__)

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=20,
    retry_on_timeout=True,
    socket_keepalive=True,
    socket_keepalive_options={}
)

# Create Redis client
redis_client = redis.Redis(connection_pool=redis_pool, decode_responses=True)


class RedisCache:
    """Redis cache utility class for managing cached data."""
    
    def __init__(self, client: redis.Redis = redis_client):
        self.client = client
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache by key.
        Returns None if key doesn't exist or has expired.
        """
        try:
            value = self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (redis.RedisError, ValueError) as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """
        Set value in cache with optional TTL.
        Returns True if successful, False otherwise.
        """
        try:
            serialized_value = json.dumps(value, default=str)
            if ttl:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                return self.client.setex(key, ttl, serialized_value)
            else:
                return self.client.set(key, serialized_value)
        except (redis.RedisError, TypeError) as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        Returns True if key was deleted, False if key didn't exist.
        """
        try:
            return bool(self.client.delete(key))
        except redis.RedisError as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        Returns True if key exists, False otherwise.
        """
        try:
            return bool(self.client.exists(key))
        except redis.RedisError as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    def flush_all(self) -> bool:
        """
        Clear all keys from cache.
        Returns True if successful, False otherwise.
        """
        try:
            return self.client.flushall()
        except redis.RedisError as e:
            logger.error(f"Error flushing cache: {e}")
            return False
    
    def get_ttl(self, key: str) -> Optional[int]:
        """
        Get TTL (time to live) for a key in seconds.
        Returns None if key doesn't exist or has no expiration.
        """
        try:
            ttl = self.client.ttl(key)
            return ttl if ttl > 0 else None
        except redis.RedisError as e:
            logger.error(f"Error getting TTL for key {key}: {e}")
            return None


def check_redis_connection() -> bool:
    """
    Check if Redis connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        redis_client.ping()
        logger.info("Redis connection successful")
        return True
    except redis.RedisError as e:
        logger.error(f"Redis connection failed: {e}")
        return False


# Create global cache instance
cache = RedisCache(redis_client)