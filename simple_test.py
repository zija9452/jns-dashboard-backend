#!/usr/bin/env python3
"""
Simple test script to verify async database operations with execute()
"""

import asyncio
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.database import engine
from src.models.user import User


async def test_async_operations():
    """Test async database operations"""

    print("Testing async database operations...")

    # Create tables first
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Test creating a session and performing operations
    async with AsyncSession(engine) as session:
        print("Async session created successfully")

        # Check if any users exist
        result = await session.execute(select(User))
        users = result.scalars().all()

        print(f"Found {len(users)} existing users")

        # Test the execute method with select
        try:
            result = await session.execute(select(User).where(User.username == "admin"))
            admin_user = result.scalar_one_or_none()

            if admin_user:
                print(f"Admin user found: {admin_user.username}")
            else:
                print("No admin user found")

            print("✓ Async execute() method works correctly with select()")
            return True

        except Exception as e:
            print(f"✗ Error with async execute(): {e}")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_async_operations())
    if success:
        print("\n✓ Async database operations work correctly!")
    else:
        print("\n✗ Async database operations failed!")