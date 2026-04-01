import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import redis
import os
from functools import wraps

class RateLimiter:
    """
    Production-ready rate limiter supporting both in-memory and Redis backends
    """

    def __init__(self):
        # Try to connect to Redis for distributed rate limiting
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.use_redis = True
        except:
            self.requests = defaultdict(list)  # IP -> list of request timestamps
            self.blocked_ips = {}  # IP -> unblock_time
            self.use_redis = False

    def _get_redis_key(self, identifier: str, key_type: str = "requests") -> str:
        """Generate Redis key for the given identifier and type"""
        return f"rate_limit:{key_type}:{identifier}"

    def is_allowed(self, identifier: str, limit: int, window: int) -> bool:
        """
        Check if a request from the given identifier is allowed

        Args:
            identifier: Unique identifier (IP address, user ID, etc.)
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        if self.use_redis:
            return self._is_allowed_redis(identifier, limit, window)
        else:
            return self._is_allowed_memory(identifier, limit, window)

    def _is_allowed_redis(self, identifier: str, limit: int, window: int) -> bool:
        """Redis-based rate limiting implementation"""
        current_time = time.time()
        requests_key = self._get_redis_key(identifier, "requests")
        blocked_key = self._get_redis_key(identifier, "blocked")

        # Check if IP is temporarily blocked
        if self.redis_client.exists(blocked_key):
            unblock_time = float(self.redis_client.get(blocked_key) or 0)
            if current_time < unblock_time:
                return False
            else:
                # Unblock if time has passed
                self.redis_client.delete(blocked_key)

        # Use Redis sorted set to track requests with timestamps
        # Remove expired entries
        self.redis_client.zremrangebyscore(requests_key, 0, current_time - window)

        # Get current count
        current_count = self.redis_client.zcard(requests_key)

        # Check if under limit
        if current_count < limit:
            # Add current request timestamp
            self.redis_client.zadd(requests_key, {str(current_time): current_time})
            # Set expiration for the key to clean up automatically
            self.redis_client.expire(requests_key, window + 60)  # Extra time for cleanup
            return True

        # Too many requests - check for repeated violations
        extended_window_start = current_time - (window * 2)
        recent_requests = self.redis_client.zcount(requests_key, extended_window_start, current_time)
        
        # Block for 1 hour if too many violations
        if recent_requests > limit * 3:
            self.redis_client.setex(blocked_key, 3600, current_time + 3600)  # 1 hour

        return False

    def _is_allowed_memory(self, identifier: str, limit: int, window: int) -> bool:
        """Memory-based rate limiting implementation (fallback)"""
        current_time = time.time()

        # Check if IP is temporarily blocked
        if identifier in self.blocked_ips:
            if current_time < self.blocked_ips[identifier]:
                return False
            else:
                # Unblock if time has passed
                del self.blocked_ips[identifier]

        # Clean old requests outside the window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < window
        ]

        # Check if under limit
        if len(self.requests[identifier]) < limit:
            self.requests[identifier].append(current_time)
            return True

        # Too many requests - consider blocking for repeated violations
        recent_requests = len([
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < window * 2  # Check for repeated violations in extended window
        ])

        # Block for 1 hour if too many violations
        if recent_requests > limit * 3:
            self.blocked_ips[identifier] = current_time + 3600  # 1 hour

        return False

    def get_reset_time(self, identifier: str, window: int) -> int:
        """Get the time when the rate limit will reset"""
        if self.use_redis:
            requests_key = self._get_redis_key(identifier, "requests")
            # Get the oldest request timestamp
            oldest_req = self.redis_client.zrange(requests_key, 0, 0, withscores=True)
            if oldest_req:
                oldest_timestamp = oldest_req[0][1]
                return int(oldest_timestamp + window - time.time())
            return 0
        else:
            if identifier in self.requests and self.requests[identifier]:
                oldest_req = min(self.requests[identifier])
                return int(oldest_req + window - time.time())
            return 0

# Global rate limiter instance
rate_limiter = RateLimiter()

class AuthRateLimiter:
    """
    Specialized rate limiter for authentication endpoints
    """

    def __init__(self):
        # Different limits for different auth endpoints
        self.login_limits = {
            'requests': 5,      # 5 login attempts
            'window': 300       # per 5 minutes (300 seconds)
        }
        self.failed_login_limits = {
            'requests': 3,      # 3 failed attempts
            'window': 900       # before temporary lockout (15 minutes)
        }

    def is_login_allowed(self, ip_address: str) -> bool:
        """
        Check if login attempt from IP is allowed
        """
        return rate_limiter.is_allowed(
            f"login_{ip_address}",
            self.login_limits['requests'],
            self.login_limits['window']
        )

    def is_failed_login_allowed(self, ip_address: str) -> bool:
        """
        Check if a failed login attempt from IP is allowed
        """
        return rate_limiter.is_allowed(
            f"failed_login_{ip_address}",
            self.failed_login_limits['requests'],
            self.failed_login_limits['window']
        )

    def record_successful_login(self, ip_address: str):
        """
        Record a successful login (resets failed login counter)
        """
        # Clear failed login attempts for this IP
        if rate_limiter.use_redis:
            # When using Redis, remove the failed login key
            failed_login_key = rate_limiter._get_redis_key(ip_address, "failed_login_requests")
            rate_limiter.redis_client.delete(failed_login_key)
        else:
            # When using in-memory storage
            if f"failed_login_{ip_address}" in rate_limiter.requests:
                del rate_limiter.requests[f"failed_login_{ip_address}"]

    def record_failed_login(self, ip_address: str) -> bool:
        """
        Record a failed login attempt

        Returns:
            True if the IP should be temporarily blocked due to too many failures
        """
        # Check if we're allowing more failed attempts
        allowed = self.is_failed_login_allowed(ip_address)
        if not allowed:
            # Add to blocked IPs
            if rate_limiter.use_redis:
                # When using Redis, set the blocked IP in Redis
                blocked_key = rate_limiter._get_redis_key(ip_address, "blocked")
                rate_limiter.redis_client.setex(blocked_key, 900, time.time() + 900)  # 15 minutes
            else:
                # When using in-memory storage
                rate_limiter.blocked_ips[ip_address] = time.time() + 900  # 15 minutes
        return not allowed

# Global auth rate limiter instance
auth_rate_limiter = AuthRateLimiter()

def get_client_ip(request) -> str:
    """
    Extract client IP from request
    This handles X-Forwarded-For header for requests through proxies/load balancers
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct client IP
    if hasattr(request, "client") and request.client:
        return request.client.host or "unknown"

    return "unknown"

# Decorator for applying rate limiting to endpoints
def rate_limit(limit: int, window: int):
    """
    Decorator to apply rate limiting to endpoints

    Usage:
    @rate_limit(10, 60)  # 10 requests per minute
    async def my_endpoint():
        pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Assuming the first argument after request is the rate limit identifier
            request = kwargs.get('request') or (args[0] if args else None)

            if request and hasattr(request, 'headers'):
                identifier = get_client_ip(request)

                if not rate_limiter.is_allowed(identifier, limit, window):
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded: {limit} requests per {window} seconds"
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator