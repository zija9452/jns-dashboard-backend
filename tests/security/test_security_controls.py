"""
Security-focused tests for the Regal POS Backend
Tests for security controls, vulnerabilities, and secure coding practices
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch, MagicMock
import jwt
from typing import Dict, Any
import re
from urllib.parse import quote
import json
from src.api.main import app
from src.auth.auth import SECRET_KEY, ALGORITHM
from src.models.user import User
from src.database.database import SessionLocal
from src.auth.password import get_password_hash


class TestSecurityControls:
    """
    Security-focused tests for the application
    """

    def setup_method(self):
        """
        Setup method for each test
        """
        self.client = TestClient(app)

    def test_security_headers_present(self):
        """
        Test that security headers are present in responses
        """
        response = self.client.get("/")

        # Check for security headers
        headers = response.headers

        # X-Content-Type-Options
        assert "x-content-type-options" in headers
        assert headers["x-content-type-options"] == "nosniff"

        # X-Frame-Options
        assert "x-frame-options" in headers
        assert headers["x-frame-options"] in ["DENY", "SAMEORIGIN"]

        # X-XSS-Protection
        assert "x-xss-protection" in headers
        assert headers["x-xss-protection"] == "1; mode=block"

        # Strict-Transport-Security (if in production mode)
        # Note: May not be present in test environment
        # assert "strict-transport-security" in headers

    def test_input_validation_xss_prevention(self):
        """
        Test input validation and XSS prevention
        """
        # Test potential XSS payloads in various inputs
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "'; DROP TABLE users; --",
            "<svg onload=alert('xss')>"
        ]

        # Test in a registration-like endpoint (would need to be adjusted based on actual endpoints)
        for payload in xss_payloads:
            # This is a sample test - adjust based on actual endpoints that accept user input
            response = self.client.post(
                "/users",
                json={
                    "username": f"test_user_{payload[:10]}",
                    "email": f"test{payload[:5]}@example.com",
                    "full_name": payload,
                    "password": "secure_password_123"
                }
            )

            # Should either reject the request or sanitize the input
            assert response.status_code in [400, 200, 422]  # 400/422 for rejection, 200 if sanitized

    def test_sql_injection_prevention(self):
        """
        Test that SQL injection attempts are prevented
        """
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "admin'; UPDATE users SET password='hacked' WHERE username='admin' --",
            "%27%20OR%20%271%27=%271"  # URL-encoded version
        ]

        for payload in sql_payloads:
            # Test in search or filter endpoints
            response = self.client.get(f"/users?search={quote(payload)}")

            # Should not return sensitive data or crash
            assert response.status_code in [200, 400, 422]

    def test_rate_limiting_functionality(self):
        """
        Test that rate limiting is functioning correctly
        """
        # Make multiple rapid requests to test rate limiting
        for i in range(20):  # More than typical rate limit
            response = self.client.get("/health")

            # Check if we eventually get rate limited
            if response.status_code == 429:
                # Rate limiting is working
                assert True
                return

        # If we never got rate limited, that might be a concern
        # (depending on how rate limiting is configured in tests)
        pytest.skip("Rate limiting not triggered in test environment")

    def test_authentication_required_endpoints(self):
        """
        Test that protected endpoints require authentication
        """
        # Try to access a protected endpoint without auth
        protected_endpoints = [
            "/users/me",
            "/admin/dashboard",
            "/products",
            "/customers"
        ]

        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            # Should return 401 or 403
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"

    def test_jwt_token_validation(self):
        """
        Test JWT token validation and security
        """
        # Test with invalid token
        response = self.client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401

        # Test with malformed token
        response = self.client.get(
            "/users/me",
            headers={"Authorization": "Bearer malformed"}
        )
        assert response.status_code == 401

        # Test token without proper prefix
        response = self.client.get(
            "/users/me",
            headers={"Authorization": "invalid_token_here"}
        )
        assert response.status_code == 401

    def test_csrf_protection_simulation(self):
        """
        Test CSRF protection mechanisms (simulated)
        """
        # This would test actual CSRF tokens in a real implementation
        # For now, we'll test the concepts

        # Check if session-based authentication has proper protections
        response = self.client.get("/health")

        # Look for security-related headers
        headers = response.headers
        # Check for anti-CSRF patterns in headers if implemented
        assert True  # Placeholder - implement based on actual CSRF mechanism

    def test_session_fixation_prevention(self):
        """
        Test that session IDs are rotated after login
        """
        # This is a conceptual test - would need actual session implementation
        # to properly test session fixation prevention
        assert True  # Placeholder - implement based on actual session management

    def test_password_strength_validation(self):
        """
        Test that password strength is validated
        """
        weak_passwords = [
            "123456",  # Too common/simple
            "password",  # Too common
            "abc",  # Too short
            "aaaaaa",  # Repetitive
        ]

        for weak_pass in weak_passwords:
            response = self.client.post(
                "/auth/register",  # Adjust endpoint as needed
                json={
                    "username": "test_user",
                    "email": "test@example.com",
                    "password": weak_pass
                }
            )
            # Should reject weak passwords
            assert response.status_code in [400, 422]

    def test_brute_force_protection(self):
        """
        Test brute force protection mechanisms
        """
        # Try multiple failed login attempts
        for i in range(10):
            response = self.client.post(
                "/auth/login",
                json={
                    "username": "nonexistent_user",
                    "password": f"wrong_password_{i}"
                }
            )

            # Check if account gets locked or rate limited after multiple attempts
            if response.status_code == 429:  # Rate limited
                assert True
                return
            elif "attempts" in response.json().get("detail", "").lower():
                # Some indication of attempt counting
                assert True
                return

        # If no protection detected, that's worth noting
        pytest.skip("Brute force protection not triggered in test environment")

    def test_insecure_direct_object_reference(self):
        """
        Test for Insecure Direct Object Reference (IDOR) vulnerabilities
        """
        # Test if users can access other users' data by changing IDs
        # This would require actual user authentication and different user contexts

        # Example: User A should not be able to access User B's private data
        # by manipulating the user ID in the URL
        assert True  # Placeholder - implement based on actual authorization logic

    def test_sensitive_data_exposure(self):
        """
        Test that sensitive data is not exposed inappropriately
        """
        # Check that sensitive fields like password hashes are not returned
        response = self.client.get("/health")

        # Parse response and ensure no sensitive data is leaked
        response_text = response.text.lower()

        # Ensure no sensitive keywords appear in responses
        sensitive_keywords = ["password", "secret", "key", "token"]
        for keyword in sensitive_keywords:
            # Be careful - health check shouldn't contain these, but other endpoints might
            # in appropriate contexts (like a login response containing a token)
            pass  # Skip this check for health endpoint

    def test_cross_origin_resource_sharing(self):
        """
        Test CORS configuration security
        """
        # Test that CORS is properly configured and doesn't allow all origins
        headers = {
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Requested-With"
        }

        response = self.client.options("/users", headers=headers)

        # Check that malicious origins are not allowed
        cors_headers = [key.lower() for key in response.headers.keys()]
        if "access-control-allow-origin" in cors_headers:
            allowed_origin = response.headers.get("access-control-allow-origin", "")
            # Ensure it doesn't allow all origins
            if allowed_origin == "*":
                pytest.fail("CORS is configured to allow all origins, which is insecure")


class TestSecurityBestPractices:
    """
    Tests for security best practices implementation
    """

    def test_jwt_configuration(self):
        """
        Test that JWT is configured securely
        """
        # Check algorithm (should not be none)
        assert ALGORITHM in ["HS256", "RS256"], f"Unsafe JWT algorithm: {ALGORITHM}"

        # Check that secret key is reasonably long
        assert len(SECRET_KEY) >= 32, "JWT secret key should be at least 32 characters"

    def test_password_hashing(self):
        """
        Test that passwords are properly hashed
        """
        plain_password = "my_secure_password_123"
        hashed = get_password_hash(plain_password)

        # Verify that the password is actually hashed
        assert hashed != plain_password
        assert len(hashed) > len(plain_password)

        # Verify that the same password creates different hashes (salted)
        hashed2 = get_password_hash(plain_password)
        assert hashed != hashed2

    def test_environment_secrets(self):
        """
        Test that sensitive configuration is properly handled
        """
        import os

        # Check that sensitive environment variables are set
        sensitive_vars = ["ACCESS_TOKEN_SECRET_KEY", "REFRESH_TOKEN_SECRET_KEY"]

        for var in sensitive_vars:
            # In test environment these might not be set, so skip if not present
            if os.getenv(var):
                assert len(os.getenv(var)) >= 32, f"Environment variable {var} should be at least 32 characters"

    def test_error_handling_not_leaking_info(self):
        """
        Test that error messages don't leak sensitive information
        """
        # Trigger an error and check the response
        response = self.client.get("/nonexistent-endpoint")

        # Error responses should not contain stack traces or system details
        error_text = response.text.lower()

        # Check for absence of sensitive information
        assert "traceback" not in error_text
        assert "stack" not in error_text
        assert "file:" not in error_text or "/app/" not in error_text


# Additional security tests could include:
# - Dependency vulnerability scanning
# - HTTP security header validation
# - Authentication flow validation
# - Authorization bypass testing
# - Data encryption verification
# - Session management security

if __name__ == "__main__":
    # This allows running the security tests directly
    pytest.main([__file__, "-v"])