from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.customer_category import (
    CustomerCategory, 
    CustomerCategoryCreate, 
    CustomerCategoryUpdate, 
    CustomerCategoryRead,
    SubCategorySchema
)
from ..models.user import User
from ..auth.session_auth import employee_required_from_session

router = APIRouter(prefix="/customer-category", tags=["Customer Category"])


@router.post("/", response_model=CustomerCategoryRead)
async def create_customer_category(
    category: CustomerCategoryCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new customer category with multiple sub-categories and options
    All sub-categories and options are saved in a single row as JSONB
    Requires employee role
    """
    # Check if category with same main_category already exists
    result = await db.execute(
        select(CustomerCategory).where(
            CustomerCategory.main_category == category.main_category
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A category with this name already exists"
        )

    # Convert sub_categories to list of dicts for JSONB storage (with proper key order)
    sub_categories_data = [
        {
            "sub_category": sc.sub_category,
            "options": sc.options
        }
        for sc in category.sub_categories
    ]

    db_category = CustomerCategory(
        main_category=category.main_category,
        sub_categories=sub_categories_data,
        branch=category.branch
    )

    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)

    return db_category


@router.get("/")
async def get_customer_categories(
    page: int = 1,
    limit: int = 50,
    branch: Optional[str] = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all customer categories with pagination
    Each category includes all its sub-categories and options
    """
    skip = (page - 1) * limit

    base_statement = select(CustomerCategory)

    if branch:
        base_statement = base_statement.where(CustomerCategory.branch == branch)

    count_statement = select(CustomerCategory.id)
    if branch:
        count_statement = count_statement.where(CustomerCategory.branch == branch)

    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    statement = base_statement.order_by(CustomerCategory.main_category).offset(skip).limit(limit)
    result = await db.execute(statement)
    categories = result.scalars().all()

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    response_data = {
        'data': [
            {
                "id": str(cat.id),
                "main_category": cat.main_category,
                "sub_categories": [
                    {
                        "sub_category": sc["sub_category"],
                        "options": sc["options"]
                    }
                    for sc in cat.sub_categories
                ],
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


@router.get("/grouped")
async def get_grouped_customer_categories(
    branch: Optional[str] = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer categories in grouped format for dropdown
    Response format:
    [
      {
        "main_category": "T-Shirt",
        "sub_categories": [
          {
            "sub_category": "Neck",
            "options": ["Round", "V-Neck", "Sherwani"]
          }
        ]
      }
    ]
    """
    statement = select(CustomerCategory)
    
    if branch:
        statement = statement.where(CustomerCategory.branch == branch)
    
    statement = statement.order_by(CustomerCategory.main_category)
    
    result = await db.execute(statement)
    categories = result.scalars().all()

    grouped_list = [
        {
            "main_category": cat.main_category,
            "sub_categories": [
                {
                    "sub_category": sc["sub_category"],
                    "options": sc["options"]
                }
                for sc in cat.sub_categories
            ]
        }
        for cat in categories
    ]

    return {"data": grouped_list}


@router.get("/{category_id}", response_model=CustomerCategoryRead)
async def get_customer_category(
    category_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific customer category by ID"""
    result = await db.execute(
        select(CustomerCategory).where(CustomerCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer category not found"
        )

    return category


@router.put("/{category_id}", response_model=CustomerCategoryRead)
async def update_customer_category(
    category_id: UUID,
    category_update: CustomerCategoryUpdate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Update a customer category - replaces all sub-categories and options"""
    result = await db.execute(
        select(CustomerCategory).where(CustomerCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer category not found"
        )

    update_data = category_update.model_dump(exclude_unset=True)
    
    # Convert sub_categories to list of dicts if present
    # Keep the order: sub_category first, then options
    if 'sub_categories' in update_data and update_data['sub_categories']:
        sub_cats = update_data['sub_categories']
        # Check if items are dicts (from JSON) or Pydantic models
        if isinstance(sub_cats[0], dict):
            # Already dicts from JSON, just ensure proper order
            update_data['sub_categories'] = [
                {
                    "sub_category": sc["sub_category"],
                    "options": sc["options"]
                }
                for sc in sub_cats
            ]
        else:
            # Pydantic models
            update_data['sub_categories'] = [
                {
                    "sub_category": sc.sub_category,
                    "options": sc.options
                }
                for sc in sub_cats
            ]

    for field, value in update_data.items():
        setattr(category, field, value)

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return category


@router.delete("/{category_id}")
async def delete_customer_category(
    category_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Delete a customer category"""
    result = await db.execute(
        select(CustomerCategory).where(CustomerCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer category not found"
        )

    await db.delete(category)
    await db.commit()

    return {"message": "Customer category deleted successfully"}


@router.delete("/bulk")
async def delete_customer_categories_bulk(
    category_ids: List[UUID],
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Delete multiple customer categories by IDs"""
    from sqlalchemy import delete as sql_delete
    
    await db.execute(
        sql_delete(CustomerCategory).where(CustomerCategory.id.in_(category_ids))
    )
    await db.commit()

    return {"message": f"{len(category_ids)} customer categories deleted successfully"}
