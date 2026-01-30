#!/usr/bin/env python3
"""
Test script to verify async authentication fixes
"""

import asyncio
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.database import engine, get_db
from src.models.user import User
from src.auth.auth import authenticate_user, create_access_token
from src.routers.auth import login
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Response


async def test_async_authentication():
    """Test async authentication functions"""

    print("Testing async authentication functions...")

    # Create a test user if one doesn't exist
    async with AsyncSession(engine) as session:
        # Check if admin user exists
        result = await session.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            # Create a test admin user
            from src.auth.password import get_password_hash
            from src.auth.auth import get_password_hash as auth_get_password_hash

            # Use the hash function from auth module
            password_hash = auth_get_password_hash("admin123")
            test_user = User(
                username="admin",
                email="admin@example.com",
                password_hash=password_hash,
                role="admin"
            )
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            print("Created test admin user")
        else:
            test_user = admin_user
            print("Using existing admin user")

    # Test the authenticate_user function directly
    async with AsyncSession(engine) as session:
        print("\nTesting authenticate_user function...")
        user = await authenticate_user("admin", "admin123", session)
        if user:
            print(f"✓ Authentication successful for user: {user.username}")
        else:
            print("✗ Authentication failed")
            return False

    # Test creating access token
    print("\nTesting access token creation...")
    access_data = {"sub": test_user.username, "user_id": str(test_user.id)}
    access_token = create_access_token(data=access_data)
    if access_token:
        print("✓ Access token created successfully")
    else:
        print("✗ Failed to create access token")
        return False

    print("\n✓ All async authentication tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_async_authentication())
    if success:
        print("\n✓ Async authentication verification completed successfully!")
    else:
        print("\n✗ Async authentication verification failed!")