#!/usr/bin/env python3
"""
Test script to verify async database operations with execute()
"""

import asyncio
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.database import engine
from src.models.user import User
from src.auth.password import get_password_hash


async def test_async_operations():
    """Test async database operations"""

    print("Testing async database operations...")

    # Create tables first
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Test creating a session and performing operations
    async with AsyncSession(engine) as session:
        print("Async session created successfully")

        # Check if admin user already exists
        result = await session.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()

        if admin_user:
            print(f"Admin user already exists: {admin_user.username}")
        else:
            print("Creating admin user...")

            # Create admin role first
            from src.models.role import Role
            role_result = await session.execute(select(Role).where(Role.name == "admin"))
            admin_role = role_result.scalar_one_or_none()

            if not admin_role:
                print("Creating admin role...")
                admin_role = Role(name="admin", permissions='{"all": true}')
                session.add(admin_role)
                await session.commit()
                await session.refresh(admin_role)

            # Create admin user
            new_admin = User(
                full_name="Admin User",
                email="admin@regalpos.com",
                username="admin",
                password_hash=get_password_hash("admin123"),
                role_id=admin_role.id,
                is_active=True
            )

            session.add(new_admin)
            await session.commit()
            await session.refresh(new_admin)

            print(f"Admin user created: {new_admin.username}")

        # Test querying the user
        result = await session.execute(select(User).where(User.username == "admin"))
        retrieved_user = result.scalar_one_or_none()

        if retrieved_user:
            print(f"Successfully retrieved user: {retrieved_user.username}")
            print(f"User email: {retrieved_user.email}")
        else:
            print("Could not retrieve the admin user")


if __name__ == "__main__":
    asyncio.run(test_async_operations())