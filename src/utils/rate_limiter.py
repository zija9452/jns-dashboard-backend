import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib

class RateLimiter:
    """
    Simple in-memory rate limiter
    In production, you'd want to use Redis or similar for distributed rate limiting
    """

    def __init__(self):
        self.requests = defaultdict(list)  # IP -> list of request timestamps
        self.blocked_ips = {}  # IP -> unblock_time

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