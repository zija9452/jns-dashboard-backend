from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional

from ..database.database import get_db
from ..models.dtf_pricing import DtfPricingSetting, DtfPricingSettingUpdate, DtfPricingSettingRead
from ..models.user import User
from ..auth.session_auth import employee_required_from_session
from ..config.branches import current_branch_name

router = APIRouter(prefix="/dtf-pricing", tags=["DTF Pricing"])


async def get_dtf_setting(db: AsyncSession, branch: Optional[str] = None) -> DtfPricingSetting:
    """This branch's DTF rule. Creates the default row (Rs. 750 per 0.5 m, 23" roll, 0.5" gap) if none exists yet."""
    branch = branch or current_branch_name()
    result = await db.execute(select(DtfPricingSetting).where(DtfPricingSetting.branch == branch))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = DtfPricingSetting(branch=branch)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    return setting


@router.get("/", response_model=DtfPricingSettingRead)
async def get_dtf_pricing(
    branch: Optional[str] = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Get the DTF rate per 0.5 m of roll, the roll width and the gap between logos."""
    return await get_dtf_setting(db, branch)


@router.put("/", response_model=DtfPricingSettingRead)
async def update_dtf_pricing(
    price_update: DtfPricingSettingUpdate,
    branch: Optional[str] = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Update the DTF rate per 0.5 m, roll width and gap."""
    if price_update.price_per_half_meter < 0:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="DTF rate cannot be negative")
    if price_update.roll_width_in <= 0:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Roll width must be more than 0")
    if price_update.gap_in < 0:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Gap cannot be negative")

    setting = await get_dtf_setting(db, branch)
    setting.price_per_half_meter = price_update.price_per_half_meter
    setting.roll_width_in = price_update.roll_width_in
    setting.gap_in = price_update.gap_in
    setting.updated_at = datetime.now()
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return setting
