import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session
from uuid import UUID
import uuid
from decimal import Decimal
from datetime import datetime

from src.services.user_service import UserService
from src.models.user import User, UserCreate, UserUpdate
from src.models.role import Role

@pytest.mark.asyncio
async def test_create_user():
    """Test creating a user"""
    # Mock the database session
    mock_db = MagicMock(spec=Session)

    # Mock the user creation
    user_create_data = UserCreate(
        full_name="Test User",
        email="test@example.com",
        username="testuser",
        password="password123",
        role_id=uuid.uuid4()
    )

    # Create a mock user object to return
    created_user = User(
        id=uuid.uuid4(),
        full_name=user_create_data.full_name,
        email=user_create_data.email,
        username=user_create_data.username,
        password_hash="hashed_password",
        role_id=user_create_data.role_id
    )

    # Mock the database operations
    with patch('src.services.user_service.get_password_hash', return_value="hashed_password"):
        with patch.object(mock_db, 'add') as mock_add:
            with patch.object(mock_db, 'commit') as mock_commit:
                with patch.object(mock_db, 'refresh', return_value=None):
                    # Call the service method
                    result = await UserService.create_user(mock_db, user_create_data)

                    # Assertions
                    assert result.full_name == user_create_data.full_name
                    assert result.email == user_create_data.email
                    assert result.username == user_create_data.username
                    assert result.password_hash == "hashed_password"

                    # Verify database operations were called
                    mock_add.assert_called_once()
                    mock_commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_user():
    """Test getting a user by ID"""
    mock_db = MagicMock(spec=Session)
    user_id = uuid.uuid4()

    # Create a mock user
    mock_user = User(
        id=user_id,
        full_name="Test User",
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        role_id=uuid.uuid4()
    )

    # Mock the database query
    mock_exec = MagicMock()
    mock_exec.first.return_value = mock_user

    with patch.object(mock_db, 'exec', return_value=mock_exec):
        result = await UserService.get_user(mock_db, user_id)

        assert result.id == user_id
        assert result.full_name == "Test User"

        # Verify the query was constructed properly
        mock_exec.first.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_not_found():
    """Test getting a user that doesn't exist"""
    mock_db = MagicMock(spec=Session)
    user_id = uuid.uuid4()

    # Mock the database query to return None
    mock_exec = MagicMock()
    mock_exec.first.return_value = None

    with patch.object(mock_db, 'exec', return_value=mock_exec):
        result = await UserService.get_user(mock_db, user_id)

        assert result is None

@pytest.mark.asyncio
async def test_get_user_by_username():
    """Test getting a user by username"""
    mock_db = MagicMock(spec=Session)
    username = "testuser"

    # Create a mock user
    mock_user = User(
        id=uuid.uuid4(),
        full_name="Test User",
        email="test@example.com",
        username=username,
        password_hash="hashed_password",
        role_id=uuid.uuid4()
    )

    # Mock the database query
    mock_exec = MagicMock()
    mock_exec.first.return_value = mock_user

    with patch.object(mock_db, 'exec', return_value=mock_exec):
        result = await UserService.get_user_by_username(mock_db, username)

        assert result.username == username
        assert result.full_name == "Test User"

@pytest.mark.asyncio
async def test_update_user():
    """Test updating a user"""
    mock_db = MagicMock(spec=Session)
    user_id = uuid.uuid4()

    # Create a mock existing user
    existing_user = User(
        id=user_id,
        full_name="Original Name",
        email="original@example.com",
        username="origuser",
        password_hash="original_hash",
        role_id=uuid.uuid4(),
        is_active=True
    )

    # Create update data
    user_update = UserUpdate(full_name="Updated Name", email="updated@example.com")

    # Mock the get_user method to return the existing user
    with patch('src.services.user_service.UserService.get_user', return_value=existing_user):
        with patch('src.services.user_service.audit_log') as mock_audit:
            with patch.object(mock_db, 'commit') as mock_commit:
                with patch.object(mock_db, 'refresh') as mock_refresh:
                    result = await UserService.update_user(mock_db, user_id, user_update)

                    # Verify the updates were applied
                    assert result.full_name == "Updated Name"
                    assert result.email == "updated@example.com"
                    # Other fields should remain unchanged
                    assert result.username == "origuser"
                    assert result.password_hash == "original_hash"

                    # Verify database operations
                    mock_commit.assert_called_once()
                    mock_refresh.assert_called_once()
                    # Audit log should be called
                    mock_audit.assert_called()

@pytest.mark.asyncio
async def test_delete_user():
    """Test deleting a user"""
    mock_db = MagicMock(spec=Session)
    user_id = uuid.uuid4()

    # Create a mock user to delete
    mock_user = User(
        id=user_id,
        full_name="To Be Deleted",
        email="delete@example.com",
        username="deleteuser",
        password_hash="hash",
        role_id=uuid.uuid4()
    )

    # Mock the get_user method to return the user
    with patch('src.services.user_service.UserService.get_user', return_value=mock_user):
        with patch('src.services.user_service.audit_log') as mock_audit:
            with patch.object(mock_db, 'delete') as mock_delete:
                with patch.object(mock_db, 'commit') as mock_commit:
                    result = await UserService.delete_user(mock_db, user_id)

                    # Verify the user was found and deletion was attempted
                    assert result is True

                    # Verify database operations
                    mock_delete.assert_called_once_with(mock_user)
                    mock_commit.assert_called_once()
                    # Audit log should be called
                    mock_audit.assert_called()

@pytest.mark.asyncio
async def test_delete_nonexistent_user():
    """Test deleting a user that doesn't exist"""
    mock_db = MagicMock(spec=Session)
    user_id = uuid.uuid4()

    # Mock the get_user method to return None (user not found)
    with patch('src.services.user_service.UserService.get_user', return_value=None):
        result = await UserService.delete_user(mock_db, user_id)

        # Verify the user was not found
        assert result is False