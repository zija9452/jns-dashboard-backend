from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.category import Category, CategoryCreate, CategoryUpdate, CategoryRead
from ..models.user import User
from ..auth.session_auth import get_current_user_from_session

router = APIRouter(prefix="/category", tags=["Category"])


@router.post("/", response_model=CategoryRead)
async def create_category(
    category: CategoryCreate,
    current_user: User = Depends(get_current_user_from_session),
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


@router.get("/")
async def get_categories(
    page: int = 1,
    limit: int = 8,
    branch: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories with optional branch filter, search and pagination
    Requires employee role
    Returns: Paginated data + total count for proper frontend pagination
    """
    # Calculate skip from page
    skip = (page - 1) * limit

    # Build base query
    base_statement = select(Category)

    # Apply branch filter (exact match)
    if branch:
        base_statement = base_statement.where(Category.branch == branch)
    
    # Apply search filter (fuzzy match on name and branch)
    if search:
        search_pattern = f"%{search}%"
        base_statement = base_statement.where(
            or_(
                Category.name.ilike(search_pattern),
                Category.branch.ilike(search_pattern)
            )
        )

    # Get total count (efficient using func.count)
    count_statement = select(func.count()).select_from(base_statement.subquery())
    count_result = await db.execute(count_statement)
    total_count = count_result.scalar_one()

    # Apply pagination and sorting
    statement = base_statement.order_by(Category.name.asc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    categories = result.scalars().all()

    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    # Prepare response with pagination info
    response_data = {
        'data': [
            {
                "id": str(cat.id),
                "name": cat.name,
                "branch": cat.branch or "",
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


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user_from_session),
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
    current_user: User = Depends(get_current_user_from_session),
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
    current_user: User = Depends(get_current_user_from_session),
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
