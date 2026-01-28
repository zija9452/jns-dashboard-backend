import pytest
from unittest.mock import MagicMock, patch
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool

@pytest.fixture(scope="function")
def mock_db_session():
    """Mock database session for testing"""
    with patch("src.database.database.SessionLocal") as mock_session:
        yield mock_session

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "full_name": "Test User",
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword",
        "role_id": "123e4567-e89b-12d3-a456-426614174000"
    }

@pytest.fixture
def sample_product_data():
    """Sample product data for testing"""
    from decimal import Decimal
    return {
        "sku": "TEST-001",
        "name": "Test Product",
        "unit_price": Decimal("19.99"),
        "cost_price": Decimal("10.00")
    }