from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from ..models.user import User, UserCreate, UserUpdate
from ..models.role import Role
from ..auth.password import get_password_hash
from ..utils.audit_logger import audit_log
from ..middleware.security import session_manager

class UserService:
    """
    Service class for handling user-related operations
    """

    @staticmethod
    async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
        """
        Create a new user
        """
        # Hash the password
        password_hash = get_password_hash(user_create.password)

        # WARNING: Storing original password in plain text for demonstration
        # This is a MAJOR SECURITY VULNERABILITY in production
        # Create the user object with all fields
        db_user = User(
            full_name=user_create.full_name,
            username=user_create.username,
            password_hash=password_hash,
            original_password=user_create.password,  # Store original for demonstration (SECURITY RISK!)
            role_id=user_create.role_id,
            phone=user_create.phone,
            address=user_create.address,
            cnic=user_create.cnic,
            branch=user_create.branch,
            company_id=user_create.company_id,  # Include company_id from user_create
            is_active=user_create.is_active if hasattr(user_create, 'is_active') else True
        )

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(db_user.id),
            entity="User",
            action="CREATE",
            changes={"full_name": user_create.full_name, "username": user_create.username}
        )

        return db_user

    @staticmethod
    async def get_user(db: AsyncSession, user_id: UUID) -> Optional[User]:
        """
        Get a user by ID
        """
        statement = select(User).where(User.id == user_id)
        result = await db.execute(statement)
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """
        Get a user by username
        """
        statement = select(User).where(User.username == username)
        result = await db.execute(statement)
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get a list of users with pagination
        """
        statement = select(User).offset(skip).limit(limit)
        result = await db.execute(statement)
        users = result.scalars().all()
        return users

    @staticmethod
    async def update_user(db: AsyncSession, user_id: UUID, user_update: UserUpdate) -> Optional[User]:
        """
        Update a user
        """
        db_user = await UserService.get_user(db, user_id)
        if not db_user:
            return None

        # Prepare update data
        update_data = user_update.model_dump(exclude_unset=True)

        # Check if password is being updated to trigger session invalidation
        password_updated = "password" in update_data

        if "password" in update_data:
            plain_password = update_data.pop("password")
            update_data["password_hash"] = get_password_hash(plain_password)
            update_data["original_password"] = plain_password

        # Update the user
        for field, value in update_data.items():
            setattr(db_user, field, value)

        await db.commit()
        await db.refresh(db_user)

        # If password was updated, invalidate all sessions for this user
        if password_updated:
            session_manager.invalidate_user_sessions(str(db_user.id))

        # Log the action - convert any UUID objects to strings for JSON serialization
        import json
        from uuid import UUID

        def convert_uuids_to_strings(obj):
            """Recursively convert UUID objects to strings in a dictionary"""
            if isinstance(obj, UUID):
                return str(obj)
            elif isinstance(obj, dict):
                return {key: convert_uuids_to_strings(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_uuids_to_strings(item) for item in obj]
            else:
                return obj

        safe_changes = convert_uuids_to_strings(update_data)

        await audit_log(
            db=db,
            user_id=str(db_user.id),
            entity="User",
            action="UPDATE",
            changes=safe_changes
        )

        return db_user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
        """
        Delete a user
        """
        db_user = await UserService.get_user(db, user_id)
        if not db_user:
            return False

        # First, delete related audit logs to avoid foreign key constraint
        from sqlalchemy import delete
        from ..models.audit_log import AuditLog
        stmt = delete(AuditLog).where(AuditLog.user_id == user_id)
        await db.execute(stmt)

        # Now delete the user
        await db.delete(db_user)
        await db.commit()

        return True