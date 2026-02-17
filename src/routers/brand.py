from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.brand import Brand, BrandCreate, BrandUpdate, BrandRead
from ..models.user import User
from ..auth.session_auth import employee_required_from_session

router = APIRouter(prefix="/brand", tags=["Brand"])


@router.post("/", response_model=BrandRead)
async def create_brand(
    brand: BrandCreate,
    current_user: User = Depends(employee_required_from_session()),
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


@router.get("/", response_model=List[BrandRead])
async def get_brands(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all brands
    Requires employee role
    """
    query = select(Brand).offset(skip).limit(limit)
    
    result = await db.execute(query)
    brands = result.scalars().all()
    
    return brands


@router.get("/{brand_id}", response_model=BrandRead)
async def get_brand(
    brand_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
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
    current_user: User = Depends(employee_required_from_session()),
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
    current_user: User = Depends(employee_required_from_session()),
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
