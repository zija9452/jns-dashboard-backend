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


def admin_cashier_production_required_from_session():
    """Require admin, cashier, or production role from session

    Narrow variant of admin_required_from_session() that also allows
    production, for the read-only vendor list the Stock In page needs
    (vendor dropdown) without granting production the rest of the
    admin-only Vendors module (create/update/delete/details).
    """
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier", "production"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, cashier, or production access required"
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
    """Require admin, cashier, employee, or warehouse role from session"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier", "employee", "warehouse"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, cashier, employee, or warehouse access required"
            )
        return current_user
    return role_checker


def admin_cashier_employee_order_booker_required_from_session():
    """Require admin, cashier, employee, warehouse, order_booker, production, or sales role from session

    Used for modules order_booker/production/sales are allowed into (customers,
    customer invoice, duplicate bill, dashboard) without granting them access to
    every other module that shares admin_cashier_employee_required_from_session.
    """
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier", "employee", "warehouse", "order_booker", "production", "sales"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, cashier, employee, warehouse, order booker, production, or sales access required"
            )
        return current_user
    return role_checker


def employee_order_booker_required_from_session():
    """Require admin, cashier, employee, order_booker, production, or sales role from session

    Narrow variant of employee_required_from_session() that also allows
    order_booker/production/sales, for the specific customer-order endpoints
    those roles use.
    """
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["employee", "cashier", "admin", "order_booker", "production", "sales"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee, cashier, admin, order booker, production, or sales access required"
            )
        return current_user
    return role_checker


def admin_employee_required_from_session():
    """Require admin, employee, production, or sales role from session (cashier NOT allowed)"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "employee", "production", "sales"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, employee, production, or sales access required. Cashiers cannot perform this action."
            )
        return current_user
    return role_checker


def admin_cashier_employee_production_required_from_session():
    """Require admin, cashier, employee, warehouse, or production role from session

    Narrow variant of admin_cashier_employee_required_from_session() that also
    allows production, for the Stock module only.
    """
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier", "employee", "warehouse", "production"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, cashier, employee, warehouse, or production access required"
            )
        return current_user
    return role_checker


def admin_cashier_employee_sales_required_from_session():
    """Require admin, cashier, employee, warehouse, or sales role from session

    Narrow variant of admin_cashier_employee_required_from_session() that also
    allows sales, for the Expenses module only.
    """
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "cashier", "employee", "warehouse", "sales"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, cashier, employee, warehouse, or sales access required"
            )
        return current_user
    return role_checker


def employee_production_required_from_session():
    """Require admin, cashier, employee, or production role from session

    Narrow variant of employee_required_from_session() that also allows
    production, for the Shop Order (restock request) endpoints.
    """
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["employee", "cashier", "admin", "production"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee, cashier, admin, or production access required"
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


def strict_admin_required_from_session():
    """Require admin or production role from session (cashier NOT allowed, unlike admin_required_from_session)

    Used for the Shop Order Approval screen, which production staff also review.
    """
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "production"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or production access required"
            )
        return current_user
    return role_checker


def admin_employee_warehouse_required_from_session():
    """Require admin, employee, or warehouse role from session (cashier NOT allowed)"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "employee", "warehouse"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, Employee, or Warehouse access required. Cashiers cannot perform this action."
            )
        return current_user
    return role_checker


def admin_employee_warehouse_production_required_from_session():
    """Require admin, employee, warehouse, or production role from session

    Narrow variant of admin_employee_warehouse_required_from_session() that
    also allows production, for the Products module only (delete product).
    """
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["admin", "employee", "warehouse", "production"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin, employee, warehouse, or production access required"
            )
        return current_user
    return role_checker