from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.user import User, UserCreate, UserUpdate, UserRead
from ..models.role import Role
from ..services.user_service import UserService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required
from ..auth.password import get_password_hash

router = APIRouter()

@router.get("/", response_model=List[UserRead])
def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Get list of users with pagination
    Requires admin role
    """
    users = UserService.get_users(db, skip=skip, limit=limit)
    return users

@router.post("/", response_model=UserRead)
def create_user(
    user_create: UserCreate,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Create a new user
    Requires admin role
    """
    # Check if role exists
    from sqlmodel import select
    role_statement = select(Role).where(Role.id == user_create.role_id)
    role = db.exec(role_statement).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role does not exist"
        )

    # Check if username or email already exists
    existing_user_by_username = UserService.get_user_by_username(db, user_create.username)
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    existing_user_by_email = db.exec(select(User).where(User.email == user_create.email)).first()
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    return UserService.create_user(db, user_create)

@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID
    Users can view their own profile, admins can view any user
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    user = UserService.get_user(db, user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions
    if str(current_user.id) != user_id and current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )

    return user

@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a specific user by ID
    Users can update their own profile, admins can update any user
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    user = UserService.get_user(db, user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions
    if str(current_user.id) != user_id and current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    # Check if trying to update role without admin privileges
    if user_update.role_id and str(current_user.id) != user_id and current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update user roles"
        )

    # If updating role, verify it exists
    if user_update.role_id:
        from sqlmodel import select
        role_statement = select(Role).where(Role.id == user_update.role_id)
        role = db.exec(role_statement).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role does not exist"
            )

    return UserService.update_user(db, user_uuid, user_update)

@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Delete a specific user by ID
    Requires admin role
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    # Prevent deletion of own account
    if str(current_user.id) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    success = UserService.delete_user(db, user_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"message": "User deleted successfully"}