from fastapi import Request, HTTPException, status, Depends
from ..models.user import User
from ..utils.session import get_session_by_token
from ..database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def get_current_user_from_session(request: Request, db: AsyncSession = Depends(get_db)):
    """Get current user from session"""
    session_token = request.cookies.get("session_token")

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    session = await get_session_by_token(session_token, db)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Get user associated with session with role loaded eagerly
    from sqlalchemy.orm import selectinload
    user_statement = select(User).options(selectinload(User.role)).where(User.id == session.user_id)
    user_result = await db.execute(user_statement)
    user = user_result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive"
        )

    return user


def admin_required_from_session():
    """Require admin role from session (admin/cashier can access)"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or cashier access required"
            )
        return current_user
    return role_checker


def cashier_required_from_session():
    """Require cashier role from session (admin/cashier can access)"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or cashier access required"
            )
        return current_user
    return role_checker


def employee_required_from_session():
    """Require employee role from session (employee, cashier, or admin can access)"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["employee", "cashier", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee, cashier, or admin access required"
            )
        return current_user
    return role_checker


def admin_cashier_employee_required_from_session():
    """Require admin, cashier, or employee role from session"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier", "employee"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, cashier, or employee access required"
            )
        return current_user
    return role_checker


def admin_employee_required_from_session():
    """Require admin or employee role from session (cashier NOT allowed)"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "employee"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or employee access required. Cashiers cannot perform this action."
            )
        return current_user
    return role_checker


def warehouse_required_from_session():
    """Require warehouse role from session (warehouse/admin can access)"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["warehouse", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Warehouse or admin access required"
            )
        return current_user
    return role_checker


def all_authenticated_from_session():
    """Require any authenticated role (admin, cashier, employee, warehouse)"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier", "employee", "warehouse"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authenticated access required"
            )
        return current_user
    return role_checker