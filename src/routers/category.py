from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.category import Category, CategoryCreate, CategoryUpdate, CategoryRead
from ..models.user import User
from ..auth.session_auth import employee_required_from_session

router = APIRouter(prefix="/category", tags=["Category"])


@router.post("/", response_model=CategoryRead)
async def create_category(
    category: CategoryCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new category with name and branch
    Requires employee role
    """
    # Check if category with same name and branch already exists
    result = await db.execute(
        select(Category).where(
            Category.name == category.name,
            Category.branch == category.branch
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name and branch already exists"
        )
    
    db_category = Category(
        name=category.name,
        branch=category.branch
    )
    
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    
    return db_category


@router.get("/", response_model=List[CategoryRead])
async def get_categories(
    skip: int = 0,
    limit: int = 100,
    branch: str = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories with optional branch filter
    Requires employee role
    """
    query = select(Category)
    
    if branch:
        query = query.where(Category.branch == branch)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return categories


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific category by ID
    Requires employee role
    """
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category


@router.put("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: UUID,
    category_update: CategoryUpdate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific category by ID
    Requires employee role
    """
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Update fields
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return category


@router.delete("/{category_id}")
async def delete_category(
    category_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a category by ID
    Requires employee role
    """
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    await db.delete(category)
    await db.commit()
    
    return {"message": "Category deleted successfully"}
