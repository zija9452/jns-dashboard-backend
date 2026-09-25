from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from ..database.database import get_db
from ..models.rush_pricing import RushPricingSetting, RushPricingSettingUpdate, RushPricingSettingRead
from ..models.user import User
from ..auth.session_auth import employee_required_from_session

router = APIRouter(prefix="/rush-pricing", tags=["Rush Pricing"])

DEFAULT_BRANCH = "European Sports Light House"


@router.get("/", response_model=RushPricingSettingRead)
async def get_rush_pricing(
    branch: str = DEFAULT_BRANCH,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Get the current fixed rush charge per piece. Creates the default row (Rs. 300) if none exists yet."""
    result = await db.execute(
        select(RushPricingSetting).where(RushPricingSetting.branch == branch)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        setting = RushPricingSetting(branch=branch)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)

    return setting


@router.put("/", response_model=RushPricingSettingRead)
async def update_rush_pricing(
    price_update: RushPricingSettingUpdate,
    branch: str = DEFAULT_BRANCH,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Update the fixed rush charge per piece."""
    result = await db.execute(
        select(RushPricingSetting).where(RushPricingSetting.branch == branch)
    )
    setting = result.scalar_one_or_none()

    if not setting:
        setting = RushPricingSetting(
            branch=branch,
            price_per_piece=price_update.price_per_piece,
            threshold_days=price_update.threshold_days
        )
        db.add(setting)
    else:
        setting.price_per_piece = price_update.price_per_piece
        setting.threshold_days = price_update.threshold_days
        setting.updated_at = datetime.now()
        db.add(setting)

    await db.commit()
    await db.refresh(setting)

    return setting
