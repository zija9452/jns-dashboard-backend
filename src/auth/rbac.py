from functools import wraps
from fastapi import HTTPException, status, Depends
from typing import List
from ..models.user import User
from .auth import get_current_user

def require_role(required_roles: List[str]):
    """
    Decorator to require specific roles for accessing endpoints
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.name not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        return current_user
    return role_checker

def require_permission(permission: str):
    """
    Decorator to require specific permissions for accessing endpoints
    """
    async def permission_checker(current_user: User = Depends(get_current_user)):
        # Check if user has the required permission
        # This is a simplified implementation - in a real system,
        # you'd have a more complex permission system
        if permission not in current_user.role.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required permission: {permission}"
            )
        return current_user
    return permission_checker

# Role-based access decorators
def admin_required():
    return require_role(["admin"])

def cashier_required():
    return require_role(["admin", "cashier"])

def employee_required():
    return require_role(["admin", "employee"])

def require_admin_or_self():
    """
    Decorator to require admin role or access to own data
    """
    async def checker(current_user: User = Depends(get_current_user)):
        def check_user(target_user_id: str):
            if current_user.role.name != "admin" and str(current_user.id) != target_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Admins can access any data, others can only access their own."
                )
            return current_user
        return check_user
    return checker