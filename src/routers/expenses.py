from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
from ..models.expense import Expense, ExpenseCreate, ExpenseUpdate, ExpenseRead
from ..services.expense_service import ExpenseService
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, cashier_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session

router = APIRouter()

@router.get("/", response_model=List[ExpenseRead])
async def get_expenses(
    created_by: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(cashier_required_from_session()),  # Employees and above can view expenses
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of expenses with pagination
    Optionally filter by created_by user ID
    Employees and admins can view expenses
    """
    created_by_uuid = None
    if created_by:
        try:
            created_by_uuid = UUID(created_by)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

    expenses = await ExpenseService.get_expenses(db, created_by=created_by_uuid, skip=skip, limit=limit)
    return expenses

@router.post("/", response_model=ExpenseRead)
async def create_expense(
    expense_create: ExpenseCreate,
    current_user: User = Depends(cashier_required_from_session()),  # Employees and above can create expenses
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new expense
    Requires employee or admin role
    """
    # Set the created_by field to the current user if not specified
    if not expense_create.created_by:
        expense_create.created_by = current_user.id

    return await ExpenseService.create_expense(db, expense_create)

@router.get("/{expense_id}", response_model=ExpenseRead)
async def get_expense(
    expense_id: str,
    current_user: User = Depends(cashier_required_from_session()),  # Employees and above can view expense details
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific expense by ID
    Employees and admins can view expense details
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

    return expense

@router.put("/{expense_id}", response_model=ExpenseRead)
async def update_expense(
    expense_id: str,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(cashier_required_from_session()),  # Only admins can update expenses
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific expense by ID
    Requires admin role
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

    return await ExpenseService.update_expense(db, expense_uuid, expense_update)

@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: User = Depends(cashier_required_from_session()),  # Only admins can delete expenses
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific expense by ID
    Requires admin role
    """
    try:
        expense_uuid = UUID(expense_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid expense ID format"
        )

    success = await ExpenseService.delete_expense(db, expense_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    return {"message": "Expense deleted successfully"}