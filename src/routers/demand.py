from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from uuid import UUID
from datetime import datetime

from ..database.database import get_db
from ..models.user import User
from ..models.demand import Demand, DemandStatus, DemandCreate
from ..auth.session_auth import employee_required_from_session, get_current_user_from_session

router = APIRouter()


@router.post("/create")
async def create_demand(
    demand_data: DemandCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Record a customer demand for an article not currently available in the shop."""
    if not demand_data.demand_text or not demand_data.demand_text.strip():
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Demand text is required"
        )

    if not demand_data.category or not demand_data.category.strip():
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Category is required"
        )

    demand = Demand(
        demand_text=demand_data.demand_text.strip(),
        category=demand_data.category.strip(),
        customer_name=demand_data.customer_name.strip() if demand_data.customer_name else None,
        customer_phone=demand_data.customer_phone.strip() if demand_data.customer_phone else None,
        status=DemandStatus.PENDING,
        created_by=current_user.id,
    )
    db.add(demand)
    await db.commit()
    await db.refresh(demand)

    return {
        "success": True,
        "id": str(demand.id),
        "message": "Demand recorded successfully"
    }


@router.get("/list")
async def get_demands(
    search_string: Optional[str] = None,
    demand_status: Optional[str] = None,
    page: int = 1,
    limit: int = 8,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """List recorded demands with optional search/status filtering."""
    if page < 1:
        page = 1
    if limit <= 0 or limit > 100:
        limit = 8
    skip = (page - 1) * limit

    conditions = []
    if search_string and search_string.strip():
        pattern = f"%{search_string.strip()}%"
        conditions.append(or_(
            Demand.demand_text.ilike(pattern),
            Demand.customer_name.ilike(pattern),
            Demand.customer_phone.ilike(pattern),
            Demand.category.ilike(pattern),
        ))

    if demand_status:
        try:
            status_enum = DemandStatus(demand_status.upper())
            conditions.append(Demand.status == status_enum)
        except ValueError:
            pass

    count_statement = select(func.count(Demand.id))
    statement = select(Demand)
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    statement = statement.order_by(Demand.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    demands = result.scalars().all()

    data = [
        {
            "id": str(demand.id),
            "demand_text": demand.demand_text,
            "category": demand.category or "",
            "customer_name": demand.customer_name or "",
            "customer_phone": demand.customer_phone or "",
            "status": demand.status.value,
            "created_at": demand.created_at.isoformat(),
            "fulfilled_at": demand.fulfilled_at.isoformat() if demand.fulfilled_at else None,
            "cancelled_at": demand.cancelled_at.isoformat() if demand.cancelled_at else None,
        }
        for demand in demands
    ]

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        "data": data,
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


@router.put("/update/{demand_id}")
async def update_demand(
    demand_id: str,
    request_data: dict,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Edit a demand's details and/or update its status (PENDING, FULFILLED, CANCELLED)."""
    try:
        demand_uuid = UUID(demand_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid demand ID format"
        )

    result = await db.execute(select(Demand).where(Demand.id == demand_uuid))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Demand not found"
        )

    if "demand_text" in request_data:
        new_text = (request_data.get("demand_text") or "").strip()
        if not new_text:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Demand text cannot be empty"
            )
        demand.demand_text = new_text

    if "category" in request_data:
        new_category = (request_data.get("category") or "").strip()
        if not new_category:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Category is required"
            )
        demand.category = new_category

    if "customer_name" in request_data:
        value = (request_data.get("customer_name") or "").strip()
        demand.customer_name = value or None

    if "customer_phone" in request_data:
        value = (request_data.get("customer_phone") or "").strip()
        demand.customer_phone = value or None

    if "status" in request_data and request_data.get("status"):
        try:
            new_status = DemandStatus(request_data["status"].upper())
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be one of: PENDING, FULFILLED, CANCELLED"
            )
        demand.status = new_status
        now = datetime.now()
        if new_status == DemandStatus.FULFILLED:
            demand.fulfilled_at = now
        elif new_status == DemandStatus.CANCELLED:
            demand.cancelled_at = now

    demand.updated_at = datetime.now()
    await db.commit()
    await db.refresh(demand)

    return {
        "success": True,
        "id": str(demand.id),
        "demand_text": demand.demand_text,
        "category": demand.category or "",
        "customer_name": demand.customer_name or "",
        "customer_phone": demand.customer_phone or "",
        "status": demand.status.value,
        "fulfilled_at": demand.fulfilled_at.isoformat() if demand.fulfilled_at else None,
        "cancelled_at": demand.cancelled_at.isoformat() if demand.cancelled_at else None,
    }


@router.delete("/{demand_id}")
async def delete_demand(
    demand_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Delete a demand record. Restricted to admin for accountability."""
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only admin can delete demand records"
        )

    try:
        demand_uuid = UUID(demand_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid demand ID format"
        )

    result = await db.execute(select(Demand).where(Demand.id == demand_uuid))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Demand not found"
        )

    await db.delete(demand)
    await db.commit()

    return {"success": True, "message": "Demand deleted successfully"}
