#!/usr/bin/env python3
"""
Test script to reproduce and fix the 401 Unauthorized error on POST /products/
"""

import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlmodel import SQLModel, select
from src.api.main import app
from src.models.user import User
from src.models.role import Role
from src.database.database import get_db
from unittest.mock import AsyncMock
import uuid
from datetime import datetime, timedelta
from jose import jwt
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test constants
TEST_SECRET_KEY = "6741b65cc7bd17c5d2e54e51e8a40b1f7de162a059e48db0901f726a0a6aa5a2"
TEST_ALGORITHM = "HS256"

def create_test_token(user_id: str, username: str = "testuser", role: str = "admin"):
    """Create a test JWT token"""
    data = {
        "sub": username,
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=15)
    }
    return jwt.encode(data, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)

async def setup_test_user():
    """Set up a test user and role in the database"""
    # Create test engine and session
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

    # For testing purposes, we'll use a simpler approach
    # We'll mock the database interaction

    # For now, let's just create a test client and make requests
    pass

def test_auth_flow():
    """Test the authentication flow to reproduce the issue"""
    client = TestClient(app)

    # Create a mock token for testing
    # This simulates what an admin user would have
    mock_user_id = str(uuid.uuid4())
    token = create_test_token(mock_user_id, "admin_user", "admin")

    print(f"Generated test token: {token[:20]}...")

    # Test GET request (should work with cashier+ roles)
    print("\nTesting GET /products/")
    response_get = client.get(
        "/products/",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"GET Response: {response_get.status_code}")
    print(f"GET Response Body: {response_get.text}")

    # Test POST request (requires admin role)
    print("\nTesting POST /products/")
    post_data = {
        "sku": "TEST001",
        "name": "Test Product",
        "unit_price": 10.99,
        "cost_price": 5.99,
        "category": "test",
        "brand": "test_brand",
        "stock_level": 100
    }

    response_post = client.post(
        "/products/",
        json=post_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"POST Response: {response_post.status_code}")
    print(f"POST Response Body: {response_post.text}")

    # Test with different role (cashier) - should fail for POST but work for GET
    print("\nTesting with cashier role (should get 403 for POST)")
    cashier_token = create_test_token(str(uuid.uuid4()), "cashier_user", "cashier")

    response_get_cashier = client.get(
        "/products/",
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    print(f"Cashier GET Response: {response_get_cashier.status_code}")

    response_post_cashier = client.post(
        "/products/",
        json=post_data,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    print(f"Cashier POST Response: {response_post_cashier.status_code} (should be 403)")
    print(f"Cashier POST Response Body: {response_post_cashier.text}")

if __name__ == "__main__":
    print("Testing authentication flow...")
    test_auth_flow()