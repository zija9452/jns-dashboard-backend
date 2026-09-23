from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID

from ..database.database import get_db
from ..models.demand_item import DemandItem, DemandItemCreate, DemandItemUpdate, DemandItemRead
from ..models.user import User
from ..auth.session_auth import get_current_user_from_session

router = APIRouter(prefix="/demand-item", tags=["Demand Item"])


@router.post("/", response_model=DemandItemRead)
async def create_demand_item(
    item: DemandItemCreate,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Add a new demand item (a specific product customers keep asking for)."""
    name = (item.name or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item name is required"
        )

    result = await db.execute(select(DemandItem).where(func.lower(DemandItem.name) == name.lower()))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An item with this name already exists: \"{existing.name}\""
        )

    db_item = DemandItem(name=name, category=(item.category or "").strip() or None)
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    return db_item


@router.get("/")
async def get_demand_items(
    search: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Search/list demand items, ordered by how often they've been demanded
    (most-demanded first) so the autocomplete surfaces likely matches fast.
    """
    if limit <= 0 or limit > 200:
        limit = 20

    from ..models.demand import Demand

    demand_count = func.count(Demand.id).label("demand_count")
    statement = (
        select(DemandItem, demand_count)
        .outerjoin(Demand, Demand.demand_item_id == DemandItem.id)
        .group_by(DemandItem.id)
    )

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(DemandItem.name.ilike(pattern))

    statement = statement.order_by(demand_count.desc(), DemandItem.name.asc()).limit(limit)
    result = await db.execute(statement)
    rows = result.all()

    return {
        "data": [
            {
                "id": str(row.DemandItem.id),
                "name": row.DemandItem.name,
                "category": row.DemandItem.category or "",
                "demand_count": row.demand_count or 0,
                "created_at": row.DemandItem.created_at.isoformat(),
            }
            for row in rows
        ]
    }


@router.put("/{item_id}", response_model=DemandItemRead)
async def update_demand_item(
    item_id: UUID,
    item_update: DemandItemUpdate,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Rename or re-categorize a demand item. Past demand records keep their text snapshot."""
    result = await db.execute(select(DemandItem).where(DemandItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demand item not found"
        )

    update_data = item_update.model_dump(exclude_unset=True)

    if "name" in update_data:
        new_name = (update_data.get("name") or "").strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Item name cannot be empty"
            )
        duplicate = await db.execute(
            select(DemandItem).where(func.lower(DemandItem.name) == new_name.lower(), DemandItem.id != item_id)
        )
        existing_dup = duplicate.scalar_one_or_none()
        if existing_dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An item with this name already exists: \"{existing_dup.name}\""
            )
        update_data["name"] = new_name

    if "category" in update_data:
        update_data["category"] = (update_data.get("category") or "").strip() or None

    for field, value in update_data.items():
        setattr(item, field, value)

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return item


@router.delete("/{item_id}")
async def delete_demand_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Delete a demand item. Existing demand records keep their text snapshot."""
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete demand items"
        )

    result = await db.execute(select(DemandItem).where(DemandItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demand item not found"
        )

    await db.delete(item)
    await db.commit()

    return {"message": "Demand item deleted successfully"}
