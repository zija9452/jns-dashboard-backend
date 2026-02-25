from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.expense_type import ExpenseType, ExpenseTypeCreate, ExpenseTypeUpdate, ExpenseTypeRead
from ..models.user import User
from ..auth.session_auth import employee_required_from_session

router = APIRouter(prefix="/expense-type", tags=["Expense Type"])


@router.post("/", response_model=ExpenseTypeRead)
async def create_expense_type(
    expense_type: ExpenseTypeCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new expense type with name only
    Requires employee role
    """
    # Check if expense type with same name already exists
    result = await db.execute(
        select(ExpenseType).where(ExpenseType.name == expense_type.name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense type with this name already exists"
        )

    db_expense_type = ExpenseType(name=expense_type.name)

    db.add(db_expense_type)
    await db.commit()
    await db.refresh(db_expense_type)

    return db_expense_type


@router.get("/")
async def get_expense_types(
    page: int = 1,
    limit: int = 8,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all expense types with pagination
    Requires employee role
    Returns: Paginated data + total count for proper frontend pagination
    """
    # Calculate skip from page
    skip = (page - 1) * limit

    # Build base query
    base_statement = select(ExpenseType)

    # Get total count
    count_statement = select(ExpenseType.id)
    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    # Apply pagination
    statement = base_statement.offset(skip).limit(limit)
    result = await db.execute(statement)
    expense_types = result.scalars().all()

    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    # Prepare response with pagination info
    response_data = {
        'data': [
            {
                "id": str(et.id),
                "name": et.name,
                "created_at": et.created_at.isoformat() if et.created_at else None
            }
            for et in expense_types
        ],
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

    return response_data


@router.get("/{expense_type_id}", response_model=ExpenseTypeRead)
async def get_expense_type(
    expense_type_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific expense type by ID
    Requires employee role
    """
    result = await db.execute(
        select(ExpenseType).where(ExpenseType.id == expense_type_id)
    )
    expense_type = result.scalar_one_or_none()

    if not expense_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense type not found"
        )

    return expense_type


@router.put("/{expense_type_id}", response_model=ExpenseTypeRead)
async def update_expense_type(
    expense_type_id: UUID,
    expense_type_update: ExpenseTypeUpdate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific expense type by ID
    Requires employee role
    """
    result = await db.execute(
        select(ExpenseType).where(ExpenseType.id == expense_type_id)
    )
    expense_type = result.scalar_one_or_none()

    if not expense_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense type not found"
        )

    # Update fields
    update_data = expense_type_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expense_type, field, value)

    db.add(expense_type)
    await db.commit()
    await db.refresh(expense_type)

    return expense_type


@router.delete("/{expense_type_id}")
async def delete_expense_type(
    expense_type_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an expense type by ID
    Requires employee role
    """
    result = await db.execute(
        select(ExpenseType).where(ExpenseType.id == expense_type_id)
    )
    expense_type = result.scalar_one_or_none()

    if not expense_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense type not found"
        )

    await db.delete(expense_type)
    await db.commit()

    return {"message": "Expense type deleted successfully"}
