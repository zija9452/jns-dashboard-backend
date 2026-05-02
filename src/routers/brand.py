from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.brand import Brand, BrandCreate, BrandUpdate, BrandRead
from ..models.user import User
from ..auth.session_auth import get_current_user_from_session

router = APIRouter(prefix="/brand", tags=["Brand"])


@router.post("/", response_model=BrandRead)
async def create_brand(
    brand: BrandCreate,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new brand with name only
    Requires employee role
    """
    # Check if brand with same name already exists
    result = await db.execute(
        select(Brand).where(Brand.name == brand.name)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brand with this name already exists"
        )
    
    db_brand = Brand(name=brand.name)
    
    db.add(db_brand)
    await db.commit()
    await db.refresh(db_brand)
    
    return db_brand


@router.post("/bulk", response_model=List[BrandRead])
async def create_brands_bulk(
    brands: List[BrandCreate],
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Add multiple brands at once
    Requires employee role
    """
    db_brands = []
    for brand_data in brands:
        # Check if brand with same name already exists
        result = await db.execute(
            select(Brand).where(Brand.name == brand_data.name)
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            db_brand = Brand(name=brand_data.name)
            db.add(db_brand)
            db_brands.append(db_brand)
    
    if db_brands:
        await db.commit()
        for brand in db_brands:
            await db.refresh(brand)
    
    return db_brands


@router.get("/")
async def get_brands(
    page: int = 1,
    limit: int = 8,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all brands with pagination and search
    Requires employee role
    Returns: Paginated data + total count for proper frontend pagination
    """
    # Calculate skip from page
    skip = (page - 1) * limit

    # Build base query
    base_statement = select(Brand)

    # Apply search filter (fuzzy match on name)
    if search:
        search_pattern = f"%{search}%"
        base_statement = base_statement.where(Brand.name.ilike(search_pattern))

    # Get total count (efficient using func.count)
    count_statement = select(func.count()).select_from(base_statement.subquery())
    count_result = await db.execute(count_statement)
    total_count = count_result.scalar_one()

    # Apply pagination and sorting
    statement = base_statement.order_by(Brand.name.asc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    brands = result.scalars().all()

    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    # Prepare response with pagination info
    response_data = {
        'data': [
            {
                "id": str(brand.id),
                "name": brand.name,
                "created_at": brand.created_at.isoformat() if brand.created_at else None
            }
            for brand in brands
        ],
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

    return response_data


@router.get("/{brand_id}", response_model=BrandRead)
async def get_brand(
    brand_id: UUID,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific brand by ID
    Requires employee role
    """
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id)
    )
    brand = result.scalar_one_or_none()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    return brand


@router.put("/{brand_id}", response_model=BrandRead)
async def update_brand(
    brand_id: UUID,
    brand_update: BrandUpdate,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific brand by ID
    Requires employee role
    """
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id)
    )
    brand = result.scalar_one_or_none()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    # Update fields
    update_data = brand_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(brand, field, value)
    
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    
    return brand


@router.delete("/{brand_id}")
async def delete_brand(
    brand_id: UUID,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a brand by ID
    Requires employee role
    """
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id)
    )
    brand = result.scalar_one_or_none()
    
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    
    await db.delete(brand)
    await db.commit()
    
    return {"message": "Brand deleted successfully"}
