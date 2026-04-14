from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import date

from ..database.database import get_db
from ..models.user import User
from ..models.expense import Expense, ExpenseCreate, ExpenseUpdate, ExpenseRead
from ..services.expense_service import ExpenseService
from ..auth.session_auth import admin_cashier_employee_required_from_session

router = APIRouter(prefix="/expenses", tags=["Expenses"])

@router.get("/")
async def get_expenses(
    page: int = 1,
    limit: int = 8,
    created_by: Optional[str] = None,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of expenses with pagination
    - Admin & Employee: Can view all expenses
    - Cashier: Can only view current date expenses
    Returns: Paginated data + total count for proper frontend pagination
    """
    # Calculate skip from page
    skip = (page - 1) * limit

    # Build base query
    base_statement = select(Expense)

    # Apply role-based filtering
    if current_user.role.name == "cashier":
        # Cashier can only see current date expenses
        today = date.today()
        base_statement = base_statement.where(Expense.expense_date == today)
    # Admin & Employee see all expenses (no filter)

    # Apply created_by filter
    if created_by:
        try:
            created_by_uuid = UUID(created_by)
            base_statement = base_statement.where(Expense.created_by == created_by_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

    # Get total count
    count_statement = select(Expense.id)
    
    # Apply role-based filtering for count
    if current_user.role.name == "cashier":
        today = date.today()
        count_statement = count_statement.where(Expense.expense_date == today)
    
    if created_by:
        try:
            created_by_uuid = UUID(created_by)
            count_statement = count_statement.where(Expense.created_by == created_by_uuid)
        except ValueError:
            pass

    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    # Apply pagination and order by expense_date ascending (oldest first)
    statement = base_statement.order_by(Expense.expense_date.asc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    expenses = result.scalars().all()

    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    # Prepare response with pagination info
    response_data = {
        'data': [
            {
                "id": str(expense.id),
                "expense": expense.expense,
                "amount": float(expense.amount),
                "expense_date": expense.expense_date.isoformat() if expense.expense_date else None,
                "branch": expense.branch or "",
                "created_by": str(expense.created_by),
                "created_at": expense.created_at.isoformat() if expense.created_at else None
            }
            for expense in expenses
        ],
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

    return response_data

@router.post("/")
async def create_expense(
    expense_create: ExpenseCreate,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new expense
    - Cashier: Can only create expenses for current date
    - Admin & Employee: Can create expenses for any date
    """
    # Restrict cashier to current date only
    if current_user.role.name == "cashier":
        if expense_create.expense_date != date.today():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cashiers can only create expenses for current date"
            )

    # Set the created_by field to the current user if not specified in the request
    if not expense_create.created_by:
        expense_create.created_by = current_user.id

    expense = await ExpenseService.create_expense(db, expense_create)
    
    # Return manually serialized response
    return {
        "id": str(expense.id),
        "expense": expense.expense,
        "amount": float(expense.amount),
        "expense_date": expense.expense_date.isoformat() if expense.expense_date else None,
        "branch": expense.branch,
        "created_by": str(expense.created_by),
        "created_at": expense.created_at.isoformat() if expense.created_at else None
    }

@router.get("/{expense_id}")
async def get_expense(
    expense_id: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific expense by ID
    Admin, cashier, and employee can view expense details
    """
    try:
        expense_uuid = UUID(expense_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expense ID format"
        )

    expense = await ExpenseService.get_expense(db, expense_uuid)

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    # Return manually serialized response
    return {
        "id": str(expense.id),
        "expense": expense.expense,
        "amount": float(expense.amount),
        "expense_date": expense.expense_date.isoformat() if expense.expense_date else None,
        "branch": expense.branch,
        "created_by": str(expense.created_by),
        "created_at": expense.created_at.isoformat() if expense.created_at else None
    }

@router.put("/{expense_id}")
async def update_expense(
    expense_id: str,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific expense by ID
    - Cashier: Can only update current date expenses
    - Admin & Employee: Can update any expense
    """
    try:
        expense_uuid = UUID(expense_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expense ID format"
        )

    expense = await ExpenseService.get_expense(db, expense_uuid)

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    # Restrict cashier from updating non-current date expenses
    if current_user.role.name == "cashier":
        if expense.expense_date != date.today():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cashiers can only update expenses for current date"
            )

    updated_expense = await ExpenseService.update_expense(db, expense_uuid, expense_update)
    
    # Return manually serialized response
    return {
        "id": str(updated_expense.id),
        "expense": updated_expense.expense,
        "amount": float(updated_expense.amount),
        "expense_date": updated_expense.expense_date.isoformat() if updated_expense.expense_date else None,
        "branch": updated_expense.branch,
        "created_by": str(updated_expense.created_by),
        "created_at": updated_expense.created_at.isoformat() if updated_expense.created_at else None
    }

@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),  # Admin, cashier, and employee can delete expenses
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific expense by ID
    - Cashier: Can only delete current date expenses
    - Admin & Employee: Can delete any expense
    """
    try:
        expense_uuid = UUID(expense_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expense ID format"
        )

    # Check if expense exists and get it
    expense = await ExpenseService.get_expense(db, expense_uuid)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    # Restrict cashier from deleting non-current date expenses
    if current_user.role.name == "cashier":
        if expense.expense_date != date.today():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cashiers can only delete expenses for current date"
            )

    success = await ExpenseService.delete_expense(db, expense_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    return {"message": "Expense deleted successfully"}