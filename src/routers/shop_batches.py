"""
Shop batches (LH / KA), BATCH_COSTING_PLAN.md sec 12: Shop Batch 001, 002 ... one count for
every shop, each with the shop vendors whose goods came in it (no bill). Made / changed in
the logged-in branch and copied to the other branches (services/shop_batch_service.py).
OPEN = picked at Stock In; CLOSED = not offered any more (its stock still sells). Only an
OPEN batch / vendor with no stock in it can be deleted / removed.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.session_auth import admin_cashier_employee_production_required_from_session
from ..config.branches import DEFAULT_BRANCH
from ..database.database import get_db, session_factories
from ..models.batch import (Batch, BatchCreate, BatchUpdate, BatchVendor, ProductBatch, BATCH_CLOSED,
                            BATCH_OPEN, LOCATION_SHOP)
from ..models.user import User
from ..models.vendor import Vendor
from ..services.shop_batch_service import (ensure_vendor_code, line_cost, line_price, mirror_batch,
                                           mirror_batch_delete, mirror_batch_vendor, mirror_batch_vendor_delete,
                                           next_shop_batch_no, peek_shop_batch_no, saved_shop_line, shop_batch_label)
from ..utils.audit_logger import audit_log
from .cash_deposit import _user_names

router = APIRouter(prefix="/shop-batches", tags=["Shop Batches"])
shop_user = admin_cashier_employee_production_required_from_session


class AddVendorRequest(BaseModel):
    vendor_id: str


def _uuid(value: str, what: str = "batch") -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {what} ID format")


async def _get_batch(db: AsyncSession, batch_id: str) -> Batch:
    batch = await db.get(Batch, _uuid(batch_id))
    if not batch or batch.location != LOCATION_SHOP:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop batch not found")
    return batch


def _require_open(batch: Batch):
    if batch.status != BATCH_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This batch is closed and cannot be changed")


async def _serialize(db: AsyncSession, batches: List[Batch]) -> List[dict]:
    ids = [b.id for b in batches]
    rows = (await db.execute(
        select(BatchVendor, Vendor).join(Vendor, BatchVendor.vendor_id == Vendor.id)
        .where(BatchVendor.batch_id.in_(ids)).order_by(BatchVendor.created_at)
    )).all() if ids else []
    bv_ids = [bv.id for bv, _ in rows]
    counts: Dict[UUID, int] = {}
    if bv_ids:
        counts = {r[0]: r[1] for r in (await db.execute(
            select(ProductBatch.batch_vendor_id, func.count()).where(ProductBatch.batch_vendor_id.in_(bv_ids))
            .group_by(ProductBatch.batch_vendor_id)
        )).all()}
    names = await _user_names(db, {u for b in batches for u in (b.created_by, b.closed_by) if u})
    by_batch: Dict[UUID, list] = {i: [] for i in ids}
    for bv, vendor in rows:
        by_batch[bv.batch_id].append({
            "id": str(bv.id),
            "vendor_id": str(vendor.id),
            "vendor_name": vendor.name.strip(),
            "vendor_code": vendor.vendor_code,
            "line_count": counts.get(bv.id, 0),
            "locked": counts.get(bv.id, 0) > 0,  # stock went in: can't be removed
        })
    return [{
        "id": str(b.id),
        "batch_no": b.batch_no,
        "label": shop_batch_label(b),
        "batch_date": b.batch_date.isoformat(),
        "status": b.status,
        "note": b.note,
        "vendors": by_batch[b.id],
        "line_count": sum(v["line_count"] for v in by_batch[b.id]),
        "vendor_count": len(by_batch[b.id]),
        "created_by_name": names.get(b.created_by),
        "created_at": b.created_at.isoformat(),
        "closed_by_name": names.get(b.closed_by) if b.closed_by else None,
        "closed_at": b.closed_at.isoformat() if b.closed_at else None,
    } for b in batches]


async def _one(db: AsyncSession, batch: Batch, warnings: Optional[List[str]] = None) -> dict:
    data = (await _serialize(db, [batch]))[0]
    data["branch_warnings"] = warnings or []
    return data


@router.get("")
async def list_shop_batches(
    status_filter: Optional[str] = None,
    vendor_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(shop_user()),
    db: AsyncSession = Depends(get_db),
):
    """Shop batches of this branch, newest first, with their vendors."""
    page, limit = max(page, 1), min(max(limit, 1), 200)
    statement = select(Batch).where(Batch.location == LOCATION_SHOP)
    if status_filter:
        statement = statement.where(Batch.status == status_filter.upper())
    if vendor_id:
        statement = statement.where(exists().where(
            BatchVendor.batch_id == Batch.id, BatchVendor.vendor_id == _uuid(vendor_id, "vendor")))
    if search and search.strip():
        term = search.strip()
        conditions = [exists().where(BatchVendor.batch_id == Batch.id, BatchVendor.vendor_id == Vendor.id,
                                     or_(Vendor.name.ilike(f"%{term}%"), Vendor.vendor_code == term)),
                      Batch.note.ilike(f"%{term}%")]
        if term.isdigit():
            conditions.append(Batch.batch_no == int(term))
        statement = statement.where(or_(*conditions))
    total = (await db.execute(select(func.count()).select_from(statement.subquery()))).scalar() or 0
    batches = (await db.execute(
        statement.order_by(Batch.batch_no.desc()).offset((page - 1) * limit).limit(limit)
    )).scalars().all()
    return {"data": await _serialize(db, batches), "page": page, "limit": limit, "total": total,
            "totalPages": (total + limit - 1) // limit}


@router.get("/next-number")
async def next_number(current_user: User = Depends(shop_user()), db: AsyncSession = Depends(get_db)):
    """The number the next shop batch will get (shown on the New Batch form)."""
    n = await peek_shop_batch_no(db)
    return {"batch_no": n, "label": f"Shop Batch {n:03d}"}


@router.get("/product/{product_id}/saved")
async def product_saved_line(
    product_id: str,
    batch_id: str,
    vendor_id: str,
    current_user: User = Depends(shop_user()),
    db: AsyncSession = Depends(get_db),
):
    """The product's line of this vendor in this shop batch, if stocked before: its saved
    cost / price (Stock In shows them locked). saved False = first time, typed by hand."""
    batch_vendor = (await db.execute(select(BatchVendor).where(
        BatchVendor.batch_id == _uuid(batch_id), BatchVendor.vendor_id == _uuid(vendor_id, "vendor")
    ))).scalar_one_or_none()
    line = await saved_shop_line(db, _uuid(product_id, "product"), batch_vendor.id) if batch_vendor else None
    if not line:
        return {"saved": False}
    return {"saved": True, "barcode": line.barcode, "cost": float(line_cost(line)),
            "selling_price": float(line_price(line)), "stock": line.stock_level or 0}


@router.get("/product/{product_id}/last")
async def product_last_shop_batch(
    product_id: str,
    vendor_id: str,
    current_user: User = Depends(shop_user()),
    db: AsyncSession = Depends(get_db),
):
    """The newest shop batch this product has saved prices in (from this vendor), for the
    Stock In default: open = picked; closed = Old Stock + a note. found False = Old Stock."""
    row = (await db.execute(
        select(ProductBatch, Batch)
        .join(BatchVendor, ProductBatch.batch_vendor_id == BatchVendor.id)
        .join(Batch, BatchVendor.batch_id == Batch.id)
        .where(ProductBatch.product_id == _uuid(product_id, "product"),
               BatchVendor.vendor_id == _uuid(vendor_id, "vendor"),
               Batch.location == LOCATION_SHOP)
        .order_by(Batch.batch_no.desc())
        .limit(1)
    )).first()
    if not row:
        return {"found": False}
    line, batch = row
    return {"found": True, "batch_id": str(batch.id), "label": shop_batch_label(batch), "status": batch.status,
            "barcode": line.barcode, "cost": float(line_cost(line)), "selling_price": float(line_price(line))}


@router.get("/{batch_id}")
async def get_shop_batch(batch_id: str, current_user: User = Depends(shop_user()), db: AsyncSession = Depends(get_db)):
    return await _one(db, await _get_batch(db, batch_id))


@router.post("")
async def create_shop_batch(data: BatchCreate, current_user: User = Depends(shop_user()),
                            db: AsyncSession = Depends(get_db)):
    """New OPEN shop batch with the next number (one count for every shop); copied to the
    other branches. Vendors are added after."""
    async with session_factories[DEFAULT_BRANCH]() as lock_db:
        batch_no = await next_shop_batch_no(lock_db, db)
        batch = Batch(location=LOCATION_SHOP, batch_no=batch_no, batch_date=data.batch_date,
                      note=(data.note or "").strip()[:500] or None, created_by=current_user.id)
        db.add(batch)
        await db.commit()
        await db.refresh(batch)
        warnings = await mirror_batch(batch)
        await lock_db.commit()  # number lock released after every branch has it
    await audit_log(db=db, user_id=str(current_user.id), entity="Batch", action="CREATE", entity_id=str(batch.id),
                    changes={"label": shop_batch_label(batch)})
    return await _one(db, batch, warnings)


@router.put("/{batch_id}")
async def update_shop_batch(batch_id: str, update: BatchUpdate, current_user: User = Depends(shop_user()),
                            db: AsyncSession = Depends(get_db)):
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    data = update.model_dump(exclude_unset=True)
    if data.get("batch_date"):
        batch.batch_date = data["batch_date"]
    if "note" in data:
        batch.note = (data["note"] or "").strip()[:500] or None
    batch.updated_at = datetime.now()
    await db.commit()
    await db.refresh(batch)
    return await _one(db, batch, await mirror_batch(batch))


@router.post("/{batch_id}/close")
async def close_shop_batch(batch_id: str, current_user: User = Depends(shop_user()), db: AsyncSession = Depends(get_db)):
    """No more Stock In into it (in every shop); its stock still sells / transfers."""
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    batch.status = BATCH_CLOSED
    batch.closed_by = current_user.id
    batch.closed_at = batch.updated_at = datetime.now()
    await db.commit()
    await db.refresh(batch)
    return await _one(db, batch, await mirror_batch(batch))


@router.delete("/{batch_id}")
async def delete_shop_batch(batch_id: str, current_user: User = Depends(shop_user()), db: AsyncSession = Depends(get_db)):
    """Only an OPEN batch no stock went into (here); its copies go too where unused."""
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    if (await db.execute(select(ProductBatch.id).where(ProductBatch.batch_id == batch.id).limit(1))).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Stock was added to this batch - it cannot be deleted. Close it instead.")
    label = shop_batch_label(batch)
    for bv in (await db.execute(select(BatchVendor).where(BatchVendor.batch_id == batch.id))).scalars().all():
        await db.delete(bv)
    await db.flush()
    await db.delete(batch)
    await db.commit()
    warnings = await mirror_batch_delete(batch)
    await audit_log(db=db, user_id=str(current_user.id), entity="Batch", action="DELETE", entity_id=batch_id,
                    changes={"label": label})
    return {"message": f"{label} deleted", "branch_warnings": warnings}


@router.post("/{batch_id}/vendors")
async def add_shop_batch_vendor(batch_id: str, body: AddVendorRequest, current_user: User = Depends(shop_user()),
                                db: AsyncSession = Depends(get_db)):
    """Add a shop vendor to an OPEN batch (no bill). The vendor gets its barcode code now."""
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    vendor = await db.get(Vendor, _uuid(body.vendor_id, "vendor"))
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    already = (await db.execute(select(BatchVendor.id).where(
        BatchVendor.batch_id == batch.id, BatchVendor.vendor_id == vendor.id))).first()
    if already:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"{vendor.name.strip()} is already in {shop_batch_label(batch)}")
    await ensure_vendor_code(db, vendor)
    batch_vendor = BatchVendor(batch_id=batch.id, vendor_id=vendor.id, bill_date=batch.batch_date,
                               invoice_total=Decimal("0"), created_by=current_user.id)
    db.add(batch_vendor)
    await db.commit()
    await db.refresh(batch_vendor)
    await db.refresh(vendor)
    warnings = await mirror_batch_vendor(batch, batch_vendor, vendor)
    return await _one(db, batch, warnings)


@router.delete("/{batch_id}/vendors/{batch_vendor_id}")
async def remove_shop_batch_vendor(batch_id: str, batch_vendor_id: str, current_user: User = Depends(shop_user()),
                                   db: AsyncSession = Depends(get_db)):
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    batch_vendor = await db.get(BatchVendor, _uuid(batch_vendor_id, "batch vendor"))
    if not batch_vendor or batch_vendor.batch_id != batch.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found in this batch")
    if (await db.execute(select(ProductBatch.id).where(ProductBatch.batch_vendor_id == batch_vendor.id).limit(1))).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Stock of this vendor was added to the batch - it cannot be removed")
    vendor = await db.get(Vendor, batch_vendor.vendor_id)
    await db.delete(batch_vendor)
    await db.commit()
    warnings = await mirror_batch_vendor_delete(batch, batch_vendor.id, vendor.name.strip() if vendor else "Vendor")
    return await _one(db, batch, warnings)
