"""
Security middleware for the Regal POS Backend
Implements additional security headers and security measures
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import secrets
import hashlib
import time


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Set security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"  # Or "SAMEORIGIN" if needed
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy (CSP) - customize based on your needs
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "report-uri /csp-report"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        return response


class CSRFProtection:
    """
    CSRF Protection utilities
    """

    def __init__(self):
        self.csrf_tokens = {}  # In production, use Redis or database
        self.token_timeout = 3600  # 1 hour

    def generate_csrf_token(self, user_id: str) -> str:
        """
        Generate a CSRF token for a user
        """
        token = secrets.token_urlsafe(32)
        timestamp = time.time()
        self.csrf_tokens[token] = {"user_id": user_id, "timestamp": timestamp}
        return token

    def validate_csrf_token(self, token: str, user_id: str) -> bool:
        """
        Validate a CSRF token for a user
        """
        if token not in self.csrf_tokens:
            return False

        token_data = self.csrf_tokens[token]
        if token_data["user_id"] != user_id:
            return False

        # Check if token has expired
        if time.time() - token_data["timestamp"] > self.token_timeout:
            del self.csrf_tokens[token]  # Clean up expired token
            return False

        # Clean up the token after validation (single-use)
        del self.csrf_tokens[token]
        return True


# Global CSRF protection instance
csrf_protection = CSRFProtection()


def get_secure_session_id():
    """
    Generate a cryptographically secure session ID
    """
    return secrets.token_urlsafe(32)


def hash_sensitive_data(data: str) -> str:
    """
    Hash sensitive data using SHA-256
    """
    return hashlib.sha256(data.encode()).hexdigest()


class SessionManager:
    """
    Session management utilities
    """

    def __init__(self):
        self.active_sessions = {}  # In production, use Redis or database

    def create_session(self, user_id: str) -> str:
        """
        Create a new session for a user
        """
        session_id = get_secure_session_id()
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time()
        }
        return session_id

    def invalidate_user_sessions(self, user_id: str):
        """
        Invalidate all sessions for a specific user (e.g., on password change)
        """
        sessions_to_remove = []
        for session_id, session_data in self.active_sessions.items():
            if session_data["user_id"] == user_id:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]

    def is_valid_session(self, session_id: str) -> bool:
        """
        Check if a session is valid and not expired
        """
        if session_id not in self.active_sessions:
            return False

        session_data = self.active_sessions[session_id]
        # Session timeout after 24 hours of inactivity
        if time.time() - session_data["last_activity"] > 24 * 3600:
            del self.active_sessions[session_id]  # Clean up expired session
            return False

        return True


# Global session manager instance
session_manager = SessionManager()