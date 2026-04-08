"""
Redis Cache Utility - Production Ready
Real-world caching implementation for FastAPI applications
"""
import redis.asyncio as redis
import json
import hashlib
from typing import Optional, Any, List, Dict
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Production-ready Redis cache manager
    Handles caching for database queries, API responses, and expensive operations
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis: Optional[redis.Redis] = None
        self.redis_url = redis_url
        self.default_ttl = 300  # 5 minutes default
        self.enabled = True
    
    async def connect(self):
        """Initialize Redis connection"""
        try:
            # For Upstash (rediss://), we need to handle SSL properly
            import ssl
            if self.redis_url.startswith("rediss://"):
                # Upstash Redis with SSL
                self.redis = redis.Redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    ssl_cert_reqs=ssl.CERT_NONE  # Disable cert verification for Upstash
                )
            else:
                # Local Redis without SSL
                self.redis = redis.Redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            await self.redis.ping()
            logger.info("✓ Redis cache connected")
        except Exception as e:
            logger.warning(f"✗ Redis connection failed: {e}. Cache disabled.")
            self.enabled = False
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis cache disconnected")
    
    def _generate_key(self, prefix: str, *args) -> str:
        """Generate cache key from arguments"""
        key_data = ":".join(str(arg) for arg in args)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.redis:
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set value in cache with TTL"""
        if not self.enabled or not self.redis:
            return
        
        try:
            ttl = ttl or self.default_ttl
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.enabled or not self.redis:
            return
        
        try:
            await self.redis.delete(key)
            logger.debug(f"Cache DELETE: {key}")
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.enabled or not self.redis:
            return
        
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cache DELETE PATTERN: {pattern} ({len(keys)} keys)")
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
    
    # ============================================================================
    # Product Cache Helpers
    # ============================================================================
    
    async def get_product_by_barcode(self, barcode: str) -> Optional[Dict]:
        """Get product from cache by barcode"""
        key = self._generate_key("product:barcode", barcode)
        return await self.get(key)
    
    async def set_product_by_barcode(self, barcode: str, product: Dict, ttl: int = 600):
        """Cache product by barcode (10 minutes)"""
        key = self._generate_key("product:barcode", barcode)
        await self.set(key, product, ttl)
    
    async def invalidate_product(self, product_id: str):
        """Invalidate all product caches for a product"""
        await self.delete_pattern(f"product:*:{product_id}")
        await self.delete_pattern(f"stock:*:{product_id}")
    
    # ============================================================================
    # Stock Cache Helpers
    # ============================================================================
    
    async def get_stock_view(self, page: int, limit: int, search: str = "") -> Optional[Dict]:
        """Get stock view from cache"""
        key = self._generate_key("stock:view", page, limit, search)
        return await self.get(key)
    
    async def set_stock_view(self, page: int, limit: int, search: str, data: Dict, ttl: int = 60):
        """Cache stock view (1 minute - changes frequently)"""
        key = self._generate_key("stock:view", page, limit, search)
        await self.set(key, data, ttl)
    
    async def invalidate_stock(self):
        """Invalidate all stock caches"""
        await self.delete_pattern("stock:view:*")
    
    # ============================================================================
    # Report Cache Helpers
    # ============================================================================

    async def get_report(self, report_type: str, params: Dict) -> Optional[str]:
        """Get cached report (base64 PDF)"""
        key = self._generate_key(f"report:{report_type}", json.dumps(params, sort_keys=True))
        return await self.get(key)

    async def set_report(self, report_type: str, params: Dict, pdf_data: str, ttl: int = 3600):
        """Cache report for 1 hour"""
        key = self._generate_key(f"report:{report_type}", json.dumps(params, sort_keys=True))
        await self.set(key, pdf_data, ttl)

    # ============================================================================
    # Dashboard Cache Helpers
    # ============================================================================

    async def get_dashboard_stats(self, params: Dict) -> Optional[Dict]:
        """Get cached dashboard stats"""
        key = self._generate_key("dashboard:stats", json.dumps(params, sort_keys=True))
        return await self.get(key)

    async def set_dashboard_stats(self, params: Dict, data: Dict, ttl: int = 300):
        """Cache dashboard stats for 5 minutes"""
        key = self._generate_key("dashboard:stats", json.dumps(params, sort_keys=True))
        await self.set(key, data, ttl)

    async def invalidate_dashboard(self):
        """Invalidate all dashboard caches"""
        await self.delete_pattern("dashboard:stats:*")


# Global cache instance
cache = CacheManager()


# ============================================================================
# Cache Decorators
# ============================================================================

def cache_product_search(ttl: int = 600):
    """
    Decorator for caching product barcode searches
    Usage: @cache_product_search(ttl=600)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            barcode = kwargs.get('barcode') or (args[1] if len(args) > 1 else None)
            
            if not barcode:
                return await func(*args, **kwargs)
            
            # Try cache first
            cached = await cache.get_product_by_barcode(barcode)
            if cached:
                return cached
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            if result:
                await cache.set_product_by_barcode(barcode, result, ttl)
            
            return result
        return wrapper
    return decorator


def cache_stock_view(ttl: int = 60):
    """
    Decorator for caching stock view queries
    Usage: @cache_stock_view(ttl=60)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            page = kwargs.get('page', 1)
            limit = kwargs.get('limit', 50)
            search = kwargs.get('search_string', '')
            
            # Try cache first
            cached = await cache.get_stock_view(page, limit, search)
            if cached:
                return cached
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            await cache.set_stock_view(page, limit, search, result, ttl)
            
            return result
        return wrapper
    return decorator
