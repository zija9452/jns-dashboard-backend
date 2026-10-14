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
from ..auth.session_auth import admin_cashier_employee_sales_required_from_session

router = APIRouter(prefix="/expenses", tags=["Expenses"])

@router.get("/")
async def get_expenses(
    page: int = 1,
    limit: int = 8,
    created_by: Optional[str] = None,
    kind: str = "daily",  # "daily" (counter), "monthly" (rent, salary... admin only) or "all"
    month: Optional[str] = None,  # "YYYY-MM": only that month's expenses
    current_user: User = Depends(admin_cashier_employee_sales_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of expenses with pagination
    - Admin & Employee: Can view all expenses (Daily, Monthly or both)
    - Cashier: Can only view current date Daily expenses
    Returns: Paginated data + total count + amount total for proper frontend pagination,
    and for admins the summary cards (today's Daily, the month's Daily and Monthly totals)
    """
    # Calculate skip from page
    skip = (page - 1) * limit

    if kind not in ("daily", "monthly", "all"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="kind must be daily, monthly or all")

    # Monthly expenses are never shown to cashiers
    if current_user.role.name == "cashier":
        kind = "daily"

    filters = []
    if kind != "all":
        filters.append(Expense.is_monthly == (kind == "monthly"))

    # Cashier can only see current date expenses
    if current_user.role.name == "cashier":
        filters.append(Expense.expense_date == date.today())

    # Month for the list filter and the summary cards (cards fall back to the current month)
    try:
        year_no, month_no = (int(part) for part in month.split("-")) if month else (date.today().year, date.today().month)
        first_day = date(year_no, month_no, 1)
        next_first_day = date(year_no + (month_no == 12), month_no % 12 + 1, 1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month format (YYYY-MM)")
    if month:
        filters.append(Expense.expense_date >= first_day)
        filters.append(Expense.expense_date < next_first_day)

    # Apply created_by filter
    if created_by:
        try:
            filters.append(Expense.created_by == UUID(created_by))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

    base_statement = select(Expense).where(*filters)

    # Get total count + amount total of the whole filtered list (not just this page)
    totals_result = await db.execute(
        select(func.count(Expense.id), func.coalesce(func.sum(Expense.amount), 0)).where(*filters)
    )
    total_count, total_amount = totals_result.one()

    # Apply pagination and order by expense_date ascending (oldest first)
    statement = base_statement.order_by(Expense.expense_date.asc(), Expense.created_at.asc()).offset(skip).limit(limit)
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
                "created_at": expense.created_at.isoformat() if expense.created_at else None,
                "is_monthly": expense.is_monthly
            }
            for expense in expenses
        ],
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages,
        'totalAmount': float(total_amount)
    }

    # Summary cards on the Expenses page (admin only)
    if current_user.role.name == "admin":
        today_result = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.is_monthly == False,
                Expense.expense_date == date.today()
            )
        )
        today_daily = today_result.scalar_one()
        month_result = await db.execute(
            select(Expense.is_monthly, func.sum(Expense.amount)).where(
                Expense.expense_date >= first_day,
                Expense.expense_date < next_first_day
            ).group_by(Expense.is_monthly)
        )
        month_totals = {is_monthly: float(amount or 0) for is_monthly, amount in month_result.all()}
        response_data['cards'] = {
            'todayDaily': float(today_daily),
            'monthDaily': month_totals.get(False, 0.0),
            'monthMonthly': month_totals.get(True, 0.0),
        }

    return response_data

@router.post("/")
async def create_expense(
    expense_create: ExpenseCreate,
    current_user: User = Depends(admin_cashier_employee_sales_required_from_session()),
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

    # Only admins may add a Monthly expense; everyone else only adds Daily ones
    if current_user.role.name != "admin":
        expense_create.is_monthly = False

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
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
        "is_monthly": expense.is_monthly
    }

@router.get("/{expense_id}")
async def get_expense(
    expense_id: str,
    current_user: User = Depends(admin_cashier_employee_sales_required_from_session()),
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

    if not expense or (current_user.role.name == "cashier" and expense.is_monthly):
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
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
        "is_monthly": expense.is_monthly
    }

@router.put("/{expense_id}")
async def update_expense(
    expense_id: str,
    expense_update: ExpenseUpdate,
    current_user: User = Depends(admin_cashier_employee_sales_required_from_session()),
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

    if not expense or (current_user.role.name == "cashier" and expense.is_monthly):
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

    # Only admins may change Daily / Monthly
    if current_user.role.name != "admin":
        expense_update.is_monthly = None

    updated_expense = await ExpenseService.update_expense(db, expense_uuid, expense_update)

    # Return manually serialized response
    return {
        "id": str(updated_expense.id),
        "expense": updated_expense.expense,
        "amount": float(updated_expense.amount),
        "expense_date": updated_expense.expense_date.isoformat() if updated_expense.expense_date else None,
        "branch": updated_expense.branch,
        "created_by": str(updated_expense.created_by),
        "created_at": updated_expense.created_at.isoformat() if updated_expense.created_at else None,
        "is_monthly": updated_expense.is_monthly
    }

@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: User = Depends(admin_cashier_employee_sales_required_from_session()),  # Admin, cashier, and employee can delete expenses
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
    if not expense or (current_user.role.name == "cashier" and expense.is_monthly):
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