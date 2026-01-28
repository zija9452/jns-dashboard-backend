import pytest
from datetime import datetime
from uuid import UUID
import uuid
from src.models.user import User, UserCreate, UserUpdate
from src.models.role import Role

def test_user_creation():
    """Test creating a new user instance"""
    user_id = uuid.uuid4()
    role_id = uuid.uuid4()

    user = User(
        id=user_id,
        full_name="John Doe",
        email="john@example.com",
        username="johndoe",
        password_hash="hashed_password_here",
        role_id=role_id,
        is_active=True
    )

    assert user.id == user_id
    assert user.full_name == "John Doe"
    assert user.email == "john@example.com"
    assert user.username == "johndoe"
    assert user.password_hash == "hashed_password_here"
    assert user.role_id == role_id
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)

def test_user_create_schema():
    """Test UserCreate schema"""
    user_create = UserCreate(
        full_name="Jane Smith",
        email="jane@example.com",
        username="janesmith",
        password="securepassword",
        role_id=uuid.uuid4()
    )

    assert user_create.full_name == "Jane Smith"
    assert user_create.email == "jane@example.com"
    assert user_create.username == "janesmith"
    assert user_create.password == "securepassword"

def test_user_update_schema():
    """Test UserUpdate schema"""
    user_update = UserUpdate(
        full_name="Updated Name",
        email="updated@example.com",
        is_active=False
    )

    assert user_update.full_name == "Updated Name"
    assert user_update.email == "updated@example.com"
    assert user_update.is_active is False

def test_user_optional_fields():
    """Test user with optional fields"""
    user_id = uuid.uuid4()
    role_id = uuid.uuid4()

    user = User(
        id=user_id,
        full_name="Bob Wilson",
        email="bob@example.com",
        username="bobwilson",
        password_hash="another_hash",
        role_id=role_id,
        is_active=True,
        meta='{"department": "sales", "employee_id": "EMP001"}'
    )

    assert user.meta == '{"department": "sales", "employee_id": "EMP001"}'