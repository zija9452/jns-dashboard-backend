from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from ..models.user import User, UserCreate, UserUpdate
from ..models.role import Role
from ..auth.password import get_password_hash
from ..utils.audit_logger import audit_log

class UserService:
    """
    Service class for handling user-related operations
    """

    @staticmethod
    async def create_user(db: Session, user_create: UserCreate) -> User:
        """
        Create a new user
        """
        # Hash the password
        password_hash = get_password_hash(user_create.password)

        # Create the user object
        db_user = User(
            full_name=user_create.full_name,
            email=user_create.email,
            username=user_create.username,
            password_hash=password_hash,
            role_id=user_create.role_id,
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
            changes={"full_name": user_create.full_name, "email": user_create.email, "username": user_create.username}
        )

        return db_user

    @staticmethod
    async def get_user(db: Session, user_id: UUID) -> Optional[User]:
        """
        Get a user by ID
        """
        statement = select(User).where(User.id == user_id)
        user = db.exec(statement).first()
        return user

    @staticmethod
    async def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """
        Get a user by username
        """
        statement = select(User).where(User.username == username)
        user = db.exec(statement).first()
        return user

    @staticmethod
    async def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get a list of users with pagination
        """
        statement = select(User).offset(skip).limit(limit)
        users = db.exec(statement).all()
        return users

    @staticmethod
    async def update_user(db: Session, user_id: UUID, user_update: UserUpdate) -> Optional[User]:
        """
        Update a user
        """
        db_user = await UserService.get_user(db, user_id)
        if not db_user:
            return None

        # Prepare update data
        update_data = user_update.dict(exclude_unset=True)
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))

        # Update the user
        for field, value in update_data.items():
            setattr(db_user, field, value)

        await db.commit()
        await db.refresh(db_user)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(db_user.id),
            entity="User",
            action="UPDATE",
            changes=update_data
        )

        return db_user

    @staticmethod
    async def delete_user(db: Session, user_id: UUID) -> bool:
        """
        Delete a user
        """
        db_user = await UserService.get_user(db, user_id)
        if not db_user:
            return False

        await db.delete(db_user)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id=str(db_user.id),
            entity="User",
            action="DELETE",
            changes={}
        )

        return True