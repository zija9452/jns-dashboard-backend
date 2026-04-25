from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.user import User, UserCreate, UserUpdate, UserRead
from ..models.role import Role
from ..services.user_service import UserService
from ..auth.auth import get_current_user
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, cashier_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session
from ..auth.password import get_password_hash
from sqlalchemy import select, or_

router = APIRouter()

@router.get("/", response_model=List[UserRead])
async def get_users(
    search_string: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of users with pagination and optional search
    Requires admin role
    """
    # Build base statement with role information
    statement = select(User, Role.name.label('role_name')).join(Role, User.role_id == Role.id, isouter=True)
    
    # Apply search filter if search_string is provided
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        statement = statement.where(
            or_(
                User.username.ilike(search_pattern),
                User.full_name.ilike(search_pattern),
                User.phone.ilike(search_pattern),
                User.cnic.ilike(search_pattern)
            )
        )
    
    statement = statement.offset(skip).limit(limit)

    result = await db.execute(statement)
    rows = result.all()
    
    # Convert to list of dicts with role_name included
    users_with_role = []
    for row in rows:
        user = row[0]
        role_name = row[1] if row[1] else 'unknown'
        
        # Convert to dict and add role_name
        user_dict = user.model_dump()
        user_dict['role_name'] = role_name
        users_with_role.append(user_dict)
    
    return users_with_role

@router.post("/", response_model=UserRead)
async def create_user(
    user_create: UserCreate,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user
    Requires admin role
    """
    from sqlalchemy import select
    from uuid import UUID
    
    # Handle role_id - can be UUID or role name (or both can be provided)
    role_id_to_use = user_create.role_id
    
    # If role_name is provided instead of role_id, look up the role by name
    if user_create.role_name:
        role_statement = select(Role).where(Role.name == user_create.role_name.lower())
        result = await db.execute(role_statement)
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{user_create.role_name}' does not exist. Available roles: admin, cashier, employee, warehouse"
            )
        role_id_to_use = role.id
    elif user_create.role_id:
        # Check if role exists by UUID
        try:
            role_statement = select(Role).where(Role.id == user_create.role_id)
            result = await db.execute(role_statement)
            role = result.scalar_one_or_none()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role does not exist"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role_id format"
            )
    else:
        # Neither role_id nor role_name provided
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either role_id or role_name must be provided"
        )
    
    # Check if username already exists
    existing_user_by_username = await UserService.get_user_by_username(db, user_create.username)
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user with the resolved role_id
    user_data = user_create.model_dump()
    user_data['role_id'] = role_id_to_use
    
    # Remove role_name from data as it's not a model field
    if 'role_name' in user_data:
        del user_data['role_name']
    
    return await UserService.create_user(db, UserCreate(**user_data))

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific user by ID
    Users can view their own profile, admins can view any user
    Requires session authentication
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    # Get user with role information
    from sqlalchemy import select
    statement = select(User, Role.name.label('role_name')).join(Role, User.role_id == Role.id, isouter=True).where(User.id == user_uuid)
    result = await db.execute(statement)
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = row[0]
    role_name = row[1] if row[1] else 'unknown'

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
    
    # Convert to dict and add role_name
    user_dict = user.model_dump()
    user_dict['role_name'] = role_name
    
    return user_dict

@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific user by ID
    Users can update their own profile, admins can update any user
    Requires session authentication
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    user = await UserService.get_user(db, user_uuid)

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

    # Handle role update - check if role_name is provided in raw data
    from sqlalchemy import select
    import json
    
    # Get raw request data to check for role_name
    update_data = user_update.model_dump(exclude_unset=True)
    
    # If role_name is provided, convert it to role_id
    if 'role_name' in update_data or hasattr(user_update, 'role_name'):
        role_name = update_data.get('role_name') or getattr(user_update, 'role_name', None)
        if role_name:
            role_statement = select(Role).where(Role.name == role_name.lower())
            role_result = await db.execute(role_statement)
            role = role_result.scalar_one_or_none()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role '{role_name}' does not exist"
                )
            update_data['role_id'] = role.id
            # Remove role_name as it's not a field in UserUpdate
            if 'role_name' in update_data:
                del update_data['role_name']
    elif user_update.role_id:
        # If role_id is provided, verify it exists
        role_statement = select(Role).where(Role.id == user_update.role_id)
        role_result = await db.execute(role_statement)
        role = role_result.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role does not exist"
            )

    # Only admins can update roles
    if 'role_id' in update_data and str(current_user.id) != user_id and current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update user roles"
        )

    # Update user with validated data
    return await UserService.update_user(db, user_uuid, UserUpdate(**update_data))

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
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

    success = await UserService.delete_user(db, user_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"message": "User deleted successfully"}