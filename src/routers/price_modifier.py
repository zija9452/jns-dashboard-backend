from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from uuid import UUID

from ..database.database import get_db
from ..models.price_modifier import (
    PriceModifier, PriceModifierCreate, PriceModifierUpdate, PriceModifierRead
)
from ..models.user import User
from ..auth.session_auth import employee_required_from_session

router = APIRouter(prefix="/price-modifiers", tags=["Price Modifiers"])


@router.post("/", response_model=PriceModifierRead)
async def create_price_modifier(
    data: PriceModifierCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Create or update the modifier for one (category, sub_category, option) - upsert."""
    result = await db.execute(
        select(PriceModifier).where(
            PriceModifier.category_id == data.category_id,
            PriceModifier.sub_category == data.sub_category,
            PriceModifier.option_value == data.option_value,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.adjustment_type = data.adjustment_type
        existing.value = data.value
        existing.updated_at = datetime.now()
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing

    modifier = PriceModifier(
        category_id=data.category_id,
        sub_category=data.sub_category,
        option_value=data.option_value,
        adjustment_type=data.adjustment_type,
        value=data.value,
    )
    db.add(modifier)
    await db.commit()
    await db.refresh(modifier)
    return modifier


@router.get("/by-category/{category_id}")
async def get_modifiers_by_category(
    category_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Returns modifiers grouped as { sub_category: { option: { type, value } } }"""
    result = await db.execute(select(PriceModifier).where(PriceModifier.category_id == category_id))
    modifiers = result.scalars().all()

    grouped: dict = {}
    for m in modifiers:
        grouped.setdefault(m.sub_category, {})[m.option_value] = {
            "type": m.adjustment_type,
            "value": float(m.value),
        }

    return {"category_id": str(category_id), "modifiers": grouped}


@router.delete("/{modifier_id}")
async def delete_price_modifier(
    modifier_id: UUID,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PriceModifier).where(PriceModifier.id == modifier_id))
    modifier = result.scalar_one_or_none()
    if not modifier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modifier not found")

    await db.delete(modifier)
    await db.commit()
    return {"message": "Modifier deleted successfully"}
