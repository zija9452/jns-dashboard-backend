from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.demand_category import (
    DemandCategory,
    DemandCategoryCreate,
    DemandCategoryUpdate,
    DemandCategoryRead
)
from ..models.user import User
from ..auth.session_auth import get_current_user_from_session

router = APIRouter(prefix="/demand-category", tags=["Demand Category"])


@router.post("/", response_model=DemandCategoryRead)
async def create_demand_category(
    category: DemandCategoryCreate,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new demand category with name only
    Requires employee role
    """
    name = (category.name or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category name is required"
        )

    # Check if category with same name already exists
    result = await db.execute(
        select(DemandCategory).where(DemandCategory.name == name)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )

    sort_order = category.sort_order
    if sort_order is not None and sort_order < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be a positive number (1 or greater)"
        )
    if sort_order is None:
        max_order_result = await db.execute(select(func.max(DemandCategory.sort_order)))
        max_order = max_order_result.scalar_one_or_none() or 0
        sort_order = max_order + 1

    db_category = DemandCategory(name=name, sort_order=sort_order)

    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)

    return db_category


@router.get("/")
async def get_demand_categories(
    page: int = 1,
    limit: int = 8,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all demand categories with pagination and search
    Requires employee role
    Returns: Paginated data + total count for proper frontend pagination
    """
    skip = (page - 1) * limit

    base_statement = select(DemandCategory)

    if search:
        search_pattern = f"%{search}%"
        base_statement = base_statement.where(DemandCategory.name.ilike(search_pattern))

    count_statement = select(func.count()).select_from(base_statement.subquery())
    count_result = await db.execute(count_statement)
    total_count = count_result.scalar_one()

    statement = base_statement.order_by(
        DemandCategory.sort_order.asc(), DemandCategory.name.asc()
    ).offset(skip).limit(limit)
    result = await db.execute(statement)
    categories = result.scalars().all()

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    response_data = {
        'data': [
            {
                "id": str(cat.id),
                "name": cat.name,
                "sort_order": cat.sort_order,
                "created_at": cat.created_at.isoformat() if cat.created_at else None
            }
            for cat in categories
        ],
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

    return response_data


@router.get("/{category_id}", response_model=DemandCategoryRead)
async def get_demand_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific demand category by ID"""
    result = await db.execute(
        select(DemandCategory).where(DemandCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demand category not found"
        )

    return category


@router.put("/{category_id}", response_model=DemandCategoryRead)
async def update_demand_category(
    category_id: UUID,
    category_update: DemandCategoryUpdate,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific demand category by ID"""
    result = await db.execute(
        select(DemandCategory).where(DemandCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demand category not found"
        )

    update_data = category_update.model_dump(exclude_unset=True)

    if 'name' in update_data:
        new_name = (update_data.get('name') or "").strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name cannot be empty"
            )
        update_data['name'] = new_name

    if 'sort_order' in update_data and update_data['sort_order'] is not None and update_data['sort_order'] < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be a positive number (1 or greater)"
        )

    for field, value in update_data.items():
        setattr(category, field, value)

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return category


@router.delete("/{category_id}")
async def delete_demand_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Delete a demand category by ID"""
    result = await db.execute(
        select(DemandCategory).where(DemandCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demand category not found"
        )

    await db.delete(category)
    await db.commit()

    return {"message": "Demand category deleted successfully"}
