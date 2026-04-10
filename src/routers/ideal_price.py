from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime

from ..database.database import get_db
from ..models.ideal_price import (
    IdealPrice,
    IdealPriceCreate,
    IdealPriceUpdate,
    IdealPriceRead
)
from ..models.user import User
from ..auth.session_auth import employee_required_from_session

router = APIRouter(prefix="/ideal-pricing", tags=["Ideal Pricing"])


@router.post("/", response_model=IdealPriceRead)
async def create_ideal_price(
    price_data: IdealPriceCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update an ideal price for a category options combination
    Requires employee role
    """
    # Check if price for this combination already exists
    result = await db.execute(
        select(IdealPrice).where(
            IdealPrice.category_id == price_data.category_id,
            IdealPrice.options_combination == price_data.options_combination
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing price instead of error
        existing.price = price_data.price
        existing.branch = price_data.branch
        existing.updated_at = datetime.now()
        
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        
        return existing

    # Create new price
    db_price = IdealPrice(
        category_id=price_data.category_id,
        options_combination=price_data.options_combination,
        price=price_data.price,
        branch=price_data.branch
    )

    db.add(db_price)
    await db.commit()
    await db.refresh(db_price)

    return db_price


@router.get("/")
async def get_ideal_prices(
    page: int = 1,
    limit: int = 50,
    category_id: Optional[str] = None,
    branch: Optional[str] = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all ideal prices with pagination and filters
    """
    skip = (page - 1) * limit

    base_statement = select(IdealPrice)

    if category_id:
        base_statement = base_statement.where(IdealPrice.category_id == UUID(category_id))

    if branch:
        base_statement = base_statement.where(IdealPrice.branch == branch)

    count_statement = select(IdealPrice.id)
    if category_id:
        count_statement = count_statement.where(IdealPrice.category_id == UUID(category_id))
    if branch:
        count_statement = count_statement.where(IdealPrice.branch == branch)

    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    statement = base_statement.order_by(IdealPrice.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    prices = result.scalars().all()

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    response_data = {
        'data': [
            {
                "id": str(price.id),
                "category_id": str(price.category_id),
                "options_combination": price.options_combination,
                "price": float(price.price),
                "branch": price.branch or "",
                "created_at": price.created_at.isoformat() if price.created_at else None,
                "updated_at": price.updated_at.isoformat() if price.updated_at else None
            }
            for price in prices
        ],
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

    return response_data


@router.get("/by-category/{category_id}")
async def get_ideal_prices_by_category(
    category_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all ideal prices for a specific category
    Returns as a dictionary for easy frontend lookup
    """
    statement = select(IdealPrice).where(IdealPrice.category_id == category_id)

    result = await db.execute(statement)
    prices = result.scalars().all()

    # Return as dictionary for easy lookup
    prices_dict = {
        price.options_combination: float(price.price)
        for price in prices
    }

    return {
        "category_id": str(category_id),
        "ideal_prices": prices_dict
    }


@router.get("/{price_id}", response_model=IdealPriceRead)
async def get_ideal_price(
    price_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific ideal price by ID"""
    result = await db.execute(
        select(IdealPrice).where(IdealPrice.id == price_id)
    )
    price = result.scalar_one_or_none()

    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ideal price not found"
        )

    return price


@router.put("/{price_id}", response_model=IdealPriceRead)
async def update_ideal_price(
    price_id: UUID,
    price_update: IdealPriceUpdate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Update an ideal price"""
    result = await db.execute(
        select(IdealPrice).where(IdealPrice.id == price_id)
    )
    price = result.scalar_one_or_none()

    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ideal price not found"
        )

    update_data = price_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(price, field, value)

    db.add(price)
    await db.commit()
    await db.refresh(price)

    return price


@router.delete("/{price_id}")
async def delete_ideal_price(
    price_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Delete an ideal price"""
    result = await db.execute(
        select(IdealPrice).where(IdealPrice.id == price_id)
    )
    price = result.scalar_one_or_none()

    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ideal price not found"
        )

    await db.delete(price)
    await db.commit()

    return {"message": "Ideal price deleted successfully"}


@router.delete("/bulk")
async def delete_ideal_prices_bulk(
    price_ids: List[UUID],
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Delete multiple ideal prices by IDs"""
    from sqlalchemy import delete as sql_delete

    await db.execute(
        sql_delete(IdealPrice).where(IdealPrice.id.in_(price_ids))
    )
    await db.commit()

    return {"message": f"{len(price_ids)} ideal prices deleted successfully"}
