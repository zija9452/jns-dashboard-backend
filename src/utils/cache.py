"""
Caching utilities for the Regal POS Backend
Implements Redis-based caching for frequently accessed data
"""
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import redis.asyncio as redis
from redis.exceptions import RedisError
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis-based cache manager for the application
    """

    def __init__(self):
        self.redis_client = None
        self.connected = False

    async def connect(self):
        """
        Connect to Redis server
        """
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=False,  # We'll handle decoding ourselves
                health_check_interval=30
            )
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False

    async def disconnect(self):
        """
        Disconnect from Redis server
        """
        if self.redis_client:
            await self.redis_client.close()
            self.connected = False

    async def set(self, key: str, value: Any, expire: Union[int, timedelta, None] = None) -> bool:
        """
        Set a value in cache

        Args:
            key: Cache key
            value: Value to cache (will be serialized)
            expire: Expiration time (seconds or timedelta)

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            logger.warning("Redis not connected, skipping cache set operation")
            return False

        try:
            # Serialize the value
            serialized_value = pickle.dumps(value)
            await self.redis_client.set(key, serialized_value, ex=expire)
            logger.debug(f"Cached value for key: {key}")
            return True
        except RedisError as e:
            logger.error(f"Redis error during set operation: {e}")
            return False
        except Exception as e:
            logger.error(f"Error serializing value for cache: {e}")
            return False

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from cache

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        if not self.connected:
            logger.debug("Redis not connected, skipping cache get operation")
            return default

        try:
            cached_value = await self.redis_client.get(key)
            if cached_value is None:
                logger.debug(f"Cache miss for key: {key}")
                return default

            logger.debug(f"Cache hit for key: {key}")
            return pickle.loads(cached_value)
        except RedisError as e:
            logger.error(f"Redis error during get operation: {e}")
            return default
        except Exception as e:
            logger.error(f"Error deserializing cached value: {e}")
            return default

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self.connected:
            logger.warning("Redis not connected, skipping cache delete operation")
            return False

        try:
            result = await self.redis_client.delete(key)
            logger.debug(f"Deleted cache key: {key}, result: {result}")
            return result > 0
        except RedisError as e:
            logger.error(f"Redis error during delete operation: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        if not self.connected:
            logger.debug("Redis not connected, assuming cache miss")
            return False

        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Redis error during exists operation: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self.connected:
            logger.warning("Redis not connected, skipping cache clear operation")
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if not keys:
                return 0

            result = await self.redis_client.delete(*keys)
            logger.info(f"Cleared {result} keys matching pattern: {pattern}")
            return result
        except RedisError as e:
            logger.error(f"Redis error during clear pattern operation: {e}")
            return 0

    async def set_json(self, key: str, value: Any, expire: Union[int, timedelta, None] = None) -> bool:
        """
        Set a JSON-serializable value in cache

        Args:
            key: Cache key
            value: JSON-serializable value
            expire: Expiration time

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            logger.warning("Redis not connected, skipping cache set operation")
            return False

        try:
            # Serialize to JSON
            json_value = json.dumps(value, default=str)
            await self.redis_client.set(key, json_value, ex=expire)
            logger.debug(f"Cached JSON value for key: {key}")
            return True
        except RedisError as e:
            logger.error(f"Redis error during set JSON operation: {e}")
            return False
        except Exception as e:
            logger.error(f"Error serializing JSON value for cache: {e}")
            return False

    async def get_json(self, key: str, default: Any = None) -> Any:
        """
        Get a JSON-serialized value from cache

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        if not self.connected:
            logger.debug("Redis not connected, skipping cache get operation")
            return default

        try:
            cached_value = await self.redis_client.get(key)
            if cached_value is None:
                logger.debug(f"JSON cache miss for key: {key}")
                return default

            logger.debug(f"JSON cache hit for key: {key}")
            return json.loads(cached_value.decode('utf-8'))
        except RedisError as e:
            logger.error(f"Redis error during get JSON operation: {e}")
            return default
        except Exception as e:
            logger.error(f"Error deserializing JSON cached value: {e}")
            return default


# Global cache manager instance
cache_manager = CacheManager()


class CacheDecorator:
    """
    Decorator for caching function results
    """

    def __init__(self, ttl: int = 300, key_prefix: str = "func_cache"):  # 5 minutes default
        self.ttl = ttl
        self.key_prefix = key_prefix

    def __call__(self, func):
        import asyncio
        from functools import wraps

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = self._generate_cache_key(func.__name__, args, kwargs)

            # Try to get from cache first
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for function: {func.__name__}")
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, expire=self.ttl)
            logger.debug(f"Function result cached for: {func.__name__}")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = self._generate_cache_key(func.__name__, args, kwargs)

            # Try to get from cache first
            cached_result = asyncio.run(cache_manager.get(cache_key))
            if cached_result is not None:
                logger.debug(f"Cache hit for function: {func.__name__}")
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            asyncio.run(cache_manager.set(cache_key, result, expire=self.ttl))
            logger.debug(f"Function result cached for: {func.__name__}")

            return result

        # Return appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    def _generate_cache_key(self, func_name: str, args, kwargs) -> str:
        """
        Generate a cache key from function name and arguments
        """
        import hashlib

        # Create a string representation of arguments
        args_str = str(args) + str(sorted(kwargs.items()))
        # Create hash to keep key length reasonable
        args_hash = hashlib.md5(args_str.encode()).hexdigest()

        return f"{self.key_prefix}:{func_name}:{args_hash}"


# Predefined cache keys for common data
USER_CACHE_PREFIX = "user:"
PRODUCT_CACHE_PREFIX = "product:"
CUSTOMER_CACHE_PREFIX = "customer:"
INVOICE_CACHE_PREFIX = "invoice:"
ROLE_CACHE_PREFIX = "role:"


def get_user_cache_key(user_id: str) -> str:
    """Get cache key for a user"""
    return f"{USER_CACHE_PREFIX}{user_id}"


def get_product_cache_key(product_id: str) -> str:
    """Get cache key for a product"""
    return f"{PRODUCT_CACHE_PREFIX}{product_id}"


def get_customer_cache_key(customer_id: str) -> str:
    """Get cache key for a customer"""
    return f"{CUSTOMER_CACHE_PREFIX}{customer_id}"