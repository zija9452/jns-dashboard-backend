from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.expense import Expense, ExpenseCreate, ExpenseUpdate, ExpenseRead
from ..services.expense_service import ExpenseService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[ExpenseRead])
def get_expenses(
    created_by: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(employee_required()),  # Employees and above can view expenses
    db: Session = Depends(get_db)
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

    expenses = ExpenseService.get_expenses(db, created_by=created_by_uuid, skip=skip, limit=limit)
    return expenses

@router.post("/", response_model=ExpenseRead)
def create_expense(
    expense_create: ExpenseCreate,
    current_user: User = Depends(employee_required()),  # Employees and above can create expenses
    db: Session = Depends(get_db)
):
    """
    Create a new expense
    Requires employee or admin role
    """
    # Set the created_by field to the current user if not specified
    if not expense_create.created_by:
        expense_create.created_by = current_user.id

    return ExpenseService.create_expense(db, expense_create)

@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    expense_id: str,
    current_user: User = Depends(employee_required()),  # Employees and above can view expense details
    db: Session = Depends(get_db)
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

    expense = ExpenseService.get_expense(db, expense_uuid)

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    return expense

@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: str,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(admin_required()),  # Only admins can update expenses
    db: Session = Depends(get_db)
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

    expense = ExpenseService.get_expense(db, expense_uuid)

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    return ExpenseService.update_expense(db, expense_uuid, expense_update)

@router.delete("/{expense_id}")
def delete_expense(
    expense_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete expenses
    db: Session = Depends(get_db)
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

    success = ExpenseService.delete_expense(db, expense_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    return {"message": "Expense deleted successfully"}

# Import statement needed for User type hint
from ..models.user import User