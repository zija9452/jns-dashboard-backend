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
    IdealPriceRead,
    IdealPriceBulkSave
)
from ..models.price_modifier import PriceModifier, AdjustmentType
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
    min_qty = price_data.min_qty or 1

    # Check if price for this combination + quantity tier already exists
    result = await db.execute(
        select(IdealPrice).where(
            IdealPrice.category_id == price_data.category_id,
            IdealPrice.options_combination == price_data.options_combination,
            IdealPrice.min_qty == min_qty
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
        min_qty=min_qty,
        price=price_data.price,
        branch=price_data.branch
    )

    db.add(db_price)
    await db.commit()
    await db.refresh(db_price)

    return db_price


@router.post("/bulk")
async def save_ideal_prices_bulk(
    data: IdealPriceBulkSave,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update many prices - and price modifiers - of one category in a single
    request and a single transaction: all saved, or none (an invalid entry rejects the
    whole request). Same upsert rules as POST /ideal-pricing/ (one row per category,
    combination, min_qty) and POST /price-modifiers/ (one per category, sub_category,
    option).
    """
    if not data.entries and not data.modifiers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No prices to save")

    wanted_modifiers: dict = {}
    for m in data.modifiers:
        if not m.sub_category or not m.option_value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each modifier needs a sub-category and an option")
        if m.adjustment_type == AdjustmentType.MULTIPLY and m.value <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Multiply value must be more than 0 ({m.sub_category}: {m.option_value})")
        wanted_modifiers[(m.sub_category, m.option_value)] = m

    # Validate everything first; a combination+tier sent twice keeps the last value.
    wanted: dict = {}
    for entry in data.entries:
        if not entry.options_combination:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each price needs an options combination")
        if entry.min_qty < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid quantity tier for {entry.options_combination}")
        if entry.price < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Price cannot be negative ({entry.options_combination})")
        wanted[(entry.options_combination, entry.min_qty)] = entry.price

    # One query for every existing price row this request touches.
    existing = {}
    if wanted:
        result = await db.execute(
            select(IdealPrice).where(
                IdealPrice.category_id == data.category_id,
                IdealPrice.options_combination.in_({combo for combo, _ in wanted})
            )
        )
        existing = {(p.options_combination, p.min_qty): p for p in result.scalars().all()}

    now = datetime.now()

    # Modifiers: one query for the category's existing ones, then upsert.
    modifiers_saved = 0
    if wanted_modifiers:
        result = await db.execute(select(PriceModifier).where(PriceModifier.category_id == data.category_id))
        existing_modifiers = {(m.sub_category, m.option_value): m for m in result.scalars().all()}
        for key, m in wanted_modifiers.items():
            row = existing_modifiers.get(key)
            if row:
                row.adjustment_type = m.adjustment_type
                row.value = m.value
                row.updated_at = now
                db.add(row)
            else:
                db.add(PriceModifier(
                    category_id=data.category_id,
                    sub_category=m.sub_category,
                    option_value=m.option_value,
                    adjustment_type=m.adjustment_type,
                    value=m.value,
                ))
            modifiers_saved += 1

    created = updated = 0
    for (combo, min_qty), price in wanted.items():
        row = existing.get((combo, min_qty))
        if row:
            row.price = price
            row.branch = data.branch
            row.updated_at = now
            db.add(row)
            updated += 1
        else:
            db.add(IdealPrice(
                category_id=data.category_id,
                options_combination=combo,
                min_qty=min_qty,
                price=price,
                branch=data.branch
            ))
            created += 1

    await db.commit()

    return {
        "success": True,
        "saved": created + updated,
        "created": created,
        "updated": updated,
        "modifiers_saved": modifiers_saved,
    }


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
                "min_qty": price.min_qty,
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

    # Return as nested dictionary: combination -> { min_qty: price } for easy lookup
    prices_dict: dict = {}
    for price in prices:
        prices_dict.setdefault(price.options_combination, {})[str(price.min_qty)] = float(price.price)

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
