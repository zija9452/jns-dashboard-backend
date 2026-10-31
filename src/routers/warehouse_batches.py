"""
Warehouse batches (BATCH_COSTING_PLAN.md sec 11): a batch is one lot (laat) reaching the
warehouse - Batch 001, 002 ... numbered once for the whole warehouse, never reused. Each
vendor whose goods came in the lot is added to it with its own bill total, freight, local
cartage, markup % and bill pictures (BatchVendor), when its goods are stocked in.
OPEN = goods still arriving (vendors can be added / edited, picked at Stock In); CLOSED =
locked. Only an OPEN batch / vendor bill with no stock in it can be deleted.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, exists
from typing import Dict, List, Optional
from uuid import UUID
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
import logging
import uuid

from ..database.database import get_db
from ..config.settings import settings
from ..models.user import User
from ..models.warehouse_vendor import WarehouseVendor
from ..models.product import Product
from ..models.stock_entry import StockEntry, StockEntryType
from ..models.batch import (Batch, BatchVendor, BatchImage, BatchCreate, BatchUpdate,
                            ProductBatch, BATCH_OPEN, BATCH_CLOSED, LOCATION_WAREHOUSE)
from ..services.batch_service import batch_label, bills_in_use, light_house_only, stocked_totals
from ..services.cloudinary_service import CloudinaryService
from ..utils.audit_logger import audit_log
from ..auth.session_auth import admin_employee_warehouse_required_from_session
from .cash_deposit import _delete_cloudinary, _user_names

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/warehouse-batches", tags=["Warehouse Batches"], dependencies=[Depends(light_house_only)])

ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
BATCH_NO_LOCK = 765434  # pg advisory lock id for batch number generation

# ---------- helpers ----------

def _parse_uuid(value: str, what: str = "batch") -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {what} ID format")


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch date")


def _parse_amount(value, field: str) -> Decimal:
    try:
        amount = Decimal(str(value if value not in (None, "") else "0"))
    except InvalidOperation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}")
    if amount < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} cannot be negative")
    return amount


def _check_amounts(invoice_total: Decimal):
    # Freight / cartage % are worked out of the invoice total
    if invoice_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill total must be more than 0")


def _pct(part: Decimal, total: Decimal) -> float:
    return round(float(part / total * 100), 2) if total else 0.0


async def _read_images(files: List[UploadFile]) -> List[bytes]:
    contents = []
    for i, file in enumerate(files, start=1):
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Picture {i}: only JPG, PNG or WebP images are allowed")
        data = await file.read()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Picture {i}: file is empty")
        if len(data) > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Picture {i}: file must be less than {max_mb}MB")
        contents.append(data)
    return contents


async def _upload_images(contents: List[bytes]) -> List[dict]:
    """Upload all pictures; on failure remove the ones already uploaded."""
    uploaded = []
    try:
        for data in contents:
            uploaded.append(await CloudinaryService.upload_slip_image(
                data, public_id=f"bill_{uuid.uuid4().hex[:12]}", folder="batch-bills"))
    except Exception as e:
        await _delete_cloudinary([u["public_id"] for u in uploaded])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return uploaded



def _batch_no(batch: Batch) -> str:
    return f"Batch {batch.batch_no:03d}"


async def _get_batch(db: AsyncSession, batch_id: str) -> Batch:
    batch = await db.get(Batch, _parse_uuid(batch_id))
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return batch


async def _get_batch_vendor(db: AsyncSession, batch: Batch, batch_vendor_id: str) -> BatchVendor:
    batch_vendor = await db.get(BatchVendor, _parse_uuid(batch_vendor_id, "batch vendor"))
    if not batch_vendor or batch_vendor.batch_id != batch.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found in this batch")
    return batch_vendor


def _require_open(batch: Batch):
    if batch.status != BATCH_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This batch is closed and cannot be changed")


def _serialize_vendor(batch: Batch, batch_vendor: BatchVendor, vendor: WarehouseVendor,
                      images: List[BatchImage], stocked: Decimal, locked: bool) -> dict:
    return {
        "id": str(batch_vendor.id),
        "label": batch_label(vendor, batch),
        "warehouse_vendor_id": str(vendor.id),
        "vendor_name": vendor.name.strip(),
        "vendor_code": vendor.vendor_code,
        "bill_date": (batch_vendor.bill_date or batch.batch_date).isoformat(),
        "invoice_total": float(batch_vendor.invoice_total),
        "freight": float(batch_vendor.freight),
        "cartage": float(batch_vendor.cartage),
        "markup_pct": float(batch_vendor.markup_pct),
        "freight_pct": _pct(batch_vendor.freight, batch_vendor.invoice_total),
        "cartage_pct": _pct(batch_vendor.cartage, batch_vendor.invoice_total),
        "extra_pct": _pct(batch_vendor.freight + batch_vendor.cartage, batch_vendor.invoice_total),
        "stocked_total": float(stocked),  # bill amount stocked in so far
        # Stock went in: bill total / freight / cartage / markup can no longer change
        "locked": locked,
        "images": [{"id": str(i.id), "url": i.file_url} for i in images],
    }


async def _serialize_batches(db: AsyncSession, batches: List[Batch], brief: bool = False) -> List[dict]:
    """Batches with their vendors (each with its bill, pictures and how much is stocked in).
    brief: for batch dropdowns - no pictures / user names (fewer DB round trips)."""
    ids = [b.id for b in batches]
    vendor_rows = (await db.execute(
        select(BatchVendor, WarehouseVendor)
        .join(WarehouseVendor, BatchVendor.warehouse_vendor_id == WarehouseVendor.id)
        .where(BatchVendor.batch_id.in_(ids))
        .order_by(BatchVendor.created_at)
    )).all() if ids else []
    bv_ids = [bv.id for bv, _ in vendor_rows]
    stocked = await stocked_totals(db, bv_ids)
    in_use = await bills_in_use(db, bv_ids)
    images: Dict[UUID, List[BatchImage]] = {i: [] for i in bv_ids}
    if not brief and bv_ids:
        for img in (await db.execute(select(BatchImage).where(BatchImage.batch_vendor_id.in_(bv_ids)))).scalars().all():
            images[img.batch_vendor_id].append(img)
    names = {} if brief else await _user_names(db, {u for b in batches for u in (b.created_by, b.closed_by)})

    by_batch: Dict[UUID, list] = {i: [] for i in ids}
    for bv, vendor in vendor_rows:
        by_batch[bv.batch_id].append((bv, vendor))

    result = []
    for batch in batches:
        vendors = [_serialize_vendor(batch, bv, v, images[bv.id], stocked[bv.id], bv.id in in_use)
                   for bv, v in by_batch[batch.id]]
        result.append({
            "id": str(batch.id),
            "batch_no": batch.batch_no,
            "label": _batch_no(batch),
            "batch_date": batch.batch_date.isoformat(),
            "status": batch.status,
            "note": batch.note,
            "vendors": vendors,
            "vendor_count": len(vendors),
            "invoice_total": sum(v["invoice_total"] for v in vendors),
            "stocked_total": sum(v["stocked_total"] for v in vendors),
            "created_by_name": names.get(batch.created_by),
            "created_at": batch.created_at.isoformat(),
            "closed_by_name": names.get(batch.closed_by) if batch.closed_by else None,
            "closed_at": batch.closed_at.isoformat() if batch.closed_at else None,
        })
    return result


async def _batch_response(db: AsyncSession, batch: Batch) -> dict:
    return (await _serialize_batches(db, [batch]))[0]


def _vendor_amounts(invoice_total, freight, cartage, markup_pct) -> dict:
    total = _parse_amount(invoice_total, "Bill total")
    _check_amounts(total)
    return {
        "invoice_total": total,
        "freight": _parse_amount(freight, "Freight"),
        "cartage": _parse_amount(cartage, "Local cartage"),
        "markup_pct": _parse_amount(markup_pct, "Markup %"),
    }


# ---------- endpoints ----------

@router.get("")
async def list_batches(
    vendor_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    brief: bool = False,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Batches (lots), newest first, each with its vendors. vendor_id: batches that vendor
    is in. search: batch number, or a vendor name / code in the batch.
    brief: for batch dropdowns - no pictures / user names."""
    page = max(page, 1)
    limit = min(max(limit, 1), 200)
    statement = select(Batch).where(Batch.location == LOCATION_WAREHOUSE)
    if vendor_id:
        statement = statement.where(exists().where(
            BatchVendor.batch_id == Batch.id, BatchVendor.warehouse_vendor_id == _parse_uuid(vendor_id, "vendor")))
    if status_filter:
        statement = statement.where(Batch.status == status_filter.upper())
    if search and search.strip():
        term = search.strip()
        vendor_match = exists().where(
            BatchVendor.batch_id == Batch.id,
            BatchVendor.warehouse_vendor_id == WarehouseVendor.id,
            or_(WarehouseVendor.name.ilike(f"%{term}%"), WarehouseVendor.vendor_code == term),
        )
        conditions = [vendor_match]
        if term.isdigit():
            conditions.append(Batch.batch_no == int(term))
        statement = statement.where(or_(*conditions))

    total = (await db.execute(select(func.count()).select_from(statement.subquery()))).scalar() or 0
    batches = (await db.execute(
        statement.order_by(Batch.batch_no.desc()).offset((page - 1) * limit).limit(limit)
    )).scalars().all()
    return {
        "data": await _serialize_batches(db, batches, brief=brief),
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": (total + limit - 1) // limit,
    }


@router.get("/product/{product_id}")
async def product_batch_lines(
    product_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """A product's warehouse stock line by line: "Old Stock" (its own barcode, cost and price;
    only when some stock is outside the batches) then each vendor's line in each batch with
    its own barcode / cost / price / stock."""
    product = await db.get(Product, _parse_uuid(product_id, "product"))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    rows = (await db.execute(
        select(ProductBatch, Batch, WarehouseVendor)
        .join(Batch, ProductBatch.batch_id == Batch.id)
        .outerjoin(BatchVendor, ProductBatch.batch_vendor_id == BatchVendor.id)
        .outerjoin(WarehouseVendor, BatchVendor.warehouse_vendor_id == WarehouseVendor.id)
        .where(ProductBatch.product_id == product.id)
        .order_by(Batch.batch_no, ProductBatch.created_at)
    )).all()

    in_batches = sum(pb.warehouse_stock or 0 for pb, _, _ in rows)
    old_cost = product.warehouse_cost if product.warehouse_cost else product.cost_price
    old_stock = (product.warehouse_stock or 0) - in_batches
    # Old Stock only while some stock is outside the batches (a product stocked straight
    # into a batch never had any)
    lines = [] if old_stock == 0 else [{
        "label": "Old Stock",
        "barcode": product.barcode,
        "vendor_name": None,
        "batch_date": None,
        "cost": float(old_cost or 0),
        "landed_cost": None,
        "selling_price": float(product.unit_price or 0),
        "warehouse_stock": old_stock,
        "status": None,
    }]
    for pb, batch, vendor in rows:
        lines.append({
            "label": _batch_no(batch),  # vendor has its own column
            "barcode": pb.barcode,
            "vendor_name": vendor.name.strip() if vendor else None,
            "batch_date": batch.batch_date.isoformat(),
            "cost": float(pb.cost),
            "landed_cost": float(pb.landed_cost),
            "selling_price": float(pb.selling_price),
            "warehouse_stock": pb.warehouse_stock or 0,
            "status": batch.status,
        })
    return {"product_id": str(product.id), "name": product.name, "lines": lines}


@router.get("/bills")
async def list_vendor_bills(
    vendor_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Every vendor's bill in every batch, newest bill first ("Vendor Bills" tab): one vendor's
    bills across the lots. status_filter: of the batch. search: vendor name / code, or batch no."""
    page = max(page, 1)
    limit = min(max(limit, 1), 200)
    statement = (
        select(BatchVendor, Batch, WarehouseVendor)
        .join(Batch, BatchVendor.batch_id == Batch.id)
        .join(WarehouseVendor, BatchVendor.warehouse_vendor_id == WarehouseVendor.id)
        .where(Batch.location == LOCATION_WAREHOUSE)
    )
    if vendor_id:
        statement = statement.where(BatchVendor.warehouse_vendor_id == _parse_uuid(vendor_id, "vendor"))
    if status_filter:
        statement = statement.where(Batch.status == status_filter.upper())
    if search and search.strip():
        term = search.strip()
        conditions = [WarehouseVendor.name.ilike(f"%{term}%"), WarehouseVendor.vendor_code == term]
        if term.isdigit():
            conditions.append(Batch.batch_no == int(term))
        statement = statement.where(or_(*conditions))

    total = (await db.execute(select(func.count()).select_from(statement.subquery()))).scalar() or 0
    rows = (await db.execute(
        statement.order_by(func.coalesce(BatchVendor.bill_date, Batch.batch_date).desc(), BatchVendor.created_at.desc())
        .offset((page - 1) * limit).limit(limit)
    )).all()
    stocked = await stocked_totals(db, [bv.id for bv, _, _ in rows])
    in_use = await bills_in_use(db, [bv.id for bv, _, _ in rows])
    return {
        "data": [{
            **_serialize_vendor(batch, bv, vendor, [], stocked[bv.id], bv.id in in_use),
            "batch_id": str(batch.id),
            "batch_no": batch.batch_no,
            "batch_status": batch.status,
        } for bv, batch, vendor in rows],
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": (total + limit - 1) // limit,
    }


@router.get("/next-number")
async def next_batch_number(
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """The number the next new batch gets (shown on Create Batch; given for real on save)."""
    max_no = (await db.execute(
        select(func.max(Batch.batch_no)).where(Batch.location == LOCATION_WAREHOUSE)
    )).scalar_one_or_none()
    return {"batch_no": (max_no or 0) + 1}


@router.get("/product/{product_id}/last")
async def product_last_source(
    product_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Where this product came from last time, for Stock In defaults: its latest batch line's
    batch (+ status) and vendor, else the vendor of its latest warehouse Stock In."""
    product_uuid = _parse_uuid(product_id, "product")
    row = (await db.execute(
        select(Batch.id, Batch.batch_no, Batch.status, BatchVendor.warehouse_vendor_id)
        .select_from(ProductBatch)
        .join(Batch, ProductBatch.batch_id == Batch.id)
        .join(BatchVendor, ProductBatch.batch_vendor_id == BatchVendor.id)
        .where(ProductBatch.product_id == product_uuid)
        .order_by(ProductBatch.updated_at.desc())
        .limit(1)
    )).first()
    if row:
        return {"batch_id": str(row[0]), "batch_no": row[1], "batch_status": row[2], "warehouse_vendor_id": str(row[3])}
    vendor_id = (await db.execute(
        select(StockEntry.warehouse_vendor_id)
        .where(StockEntry.product_id == product_uuid, StockEntry.type == StockEntryType.IN,
               StockEntry.warehouse_vendor_id.isnot(None))
        .order_by(StockEntry.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    return {"batch_id": None, "batch_no": None, "batch_status": None,
            "warehouse_vendor_id": str(vendor_id) if vendor_id else None}


@router.get("/{batch_id}")
async def get_batch(
    batch_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    return await _batch_response(db, await _get_batch(db, batch_id))


@router.post("")
async def create_batch(
    data: BatchCreate,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """New OPEN batch (lot) with the next warehouse batch number; vendors are added later."""
    batch = Batch(
        location=LOCATION_WAREHOUSE,
        batch_no=0,
        batch_date=data.batch_date,
        note=(data.note or "").strip()[:500] or None,
        created_by=current_user.id,
    )
    # Transaction-level lock: held until commit, so two creates never get the same number
    await db.execute(select(func.pg_advisory_xact_lock(BATCH_NO_LOCK)))
    max_no = (await db.execute(
        select(func.max(Batch.batch_no)).where(Batch.location == LOCATION_WAREHOUSE)
    )).scalar_one_or_none()
    batch.batch_no = (max_no or 0) + 1
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    await audit_log(db=db, user_id=str(current_user.id), entity="Batch", action="CREATE", entity_id=str(batch.id),
                    changes={"label": _batch_no(batch)})
    return await _batch_response(db, batch)


@router.put("/{batch_id}")
async def update_batch(
    batch_id: str,
    update: BatchUpdate,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Edit an OPEN batch's date / note (the number stays)."""
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    data = update.model_dump(exclude_unset=True)
    if "batch_date" in data and data["batch_date"] is None:
        del data["batch_date"]
    if "note" in data:
        data["note"] = (data["note"] or "").strip()[:500] or None
    for field, value in data.items():
        setattr(batch, field, value)
    batch.updated_at = datetime.now()
    await db.commit()
    await db.refresh(batch)
    await audit_log(db=db, user_id=str(current_user.id), entity="Batch", action="UPDATE", entity_id=str(batch.id),
                    changes={k: str(v) for k, v in data.items()})
    return await _batch_response(db, batch)


@router.post("/{batch_id}/close")
async def close_batch(
    batch_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """All goods of the lot arrived: lock the batch."""
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    batch.status = BATCH_CLOSED
    batch.closed_by = current_user.id
    batch.closed_at = datetime.now()
    batch.updated_at = batch.closed_at
    await db.commit()
    await db.refresh(batch)
    await audit_log(db=db, user_id=str(current_user.id), entity="Batch", action="UPDATE", entity_id=str(batch.id),
                    changes={"status": BATCH_CLOSED})
    return await _batch_response(db, batch)


@router.delete("/{batch_id}")
async def delete_batch(
    batch_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Only an OPEN batch that no stock went into (its vendor bills and pictures go too)."""
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    used = (await db.execute(select(ProductBatch.id).where(ProductBatch.batch_id == batch.id).limit(1))).first()
    if used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Stock was added to this batch - it cannot be deleted. Close it instead.")
    label = _batch_no(batch)
    images = (await db.execute(select(BatchImage).where(BatchImage.batch_id == batch.id))).scalars().all()
    public_ids = [i.public_id for i in images]
    for image in images:
        await db.delete(image)
    for batch_vendor in (await db.execute(select(BatchVendor).where(BatchVendor.batch_id == batch.id))).scalars().all():
        await db.delete(batch_vendor)
    await db.flush()
    await db.delete(batch)
    await db.commit()
    await _delete_cloudinary(public_ids)
    await audit_log(db=db, user_id=str(current_user.id), entity="Batch", action="DELETE", entity_id=batch_id,
                    changes={"label": label})
    return {"message": f"{label} deleted"}


# ---------- vendors in a batch ----------

@router.post("/{batch_id}/vendors")
async def add_batch_vendor(
    batch_id: str,
    warehouse_vendor_id: str = Form(...),
    bill_date: Optional[str] = Form(None),
    invoice_total: str = Form(...),
    freight: str = Form("0"),
    cartage: str = Form("0"),
    markup_pct: str = Form("0"),
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """A vendor's goods of this lot arrived: add its bill (total, freight, cartage, markup %,
    pictures) to the OPEN batch. A vendor is in a batch once. The bill's figures never change
    after (prices and labels come from them) - a wrong one is removed while no stock is in it
    and added again; only pictures can be added / deleted."""
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    vendor = await db.get(WarehouseVendor, _parse_uuid(warehouse_vendor_id, "vendor"))
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse vendor not found")
    already = (await db.execute(select(BatchVendor.id).where(
        BatchVendor.batch_id == batch.id, BatchVendor.warehouse_vendor_id == vendor.id))).first()
    if already:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"{vendor.name.strip()} is already in {_batch_no(batch)} - edit its bill instead")
    batch_vendor = BatchVendor(batch_id=batch.id, warehouse_vendor_id=vendor.id, created_by=current_user.id,
                               bill_date=_parse_date(bill_date) if bill_date else batch.batch_date,
                               **_vendor_amounts(invoice_total, freight, cartage, markup_pct))
    uploaded = await _upload_images(await _read_images(files))
    try:
        db.add(batch_vendor)
        await db.flush()
        for u in uploaded:
            db.add(BatchImage(batch_id=batch.id, batch_vendor_id=batch_vendor.id, file_url=u["url"], public_id=u["public_id"]))
        await db.commit()
    except Exception:
        await db.rollback()
        await _delete_cloudinary([u["public_id"] for u in uploaded])
        raise
    await audit_log(db=db, user_id=str(current_user.id), entity="BatchVendor", action="CREATE", entity_id=str(batch_vendor.id),
                    changes={"label": batch_label(vendor, batch), "invoice_total": str(batch_vendor.invoice_total)})
    return await _batch_response(db, batch)


@router.delete("/{batch_id}/vendors/{batch_vendor_id}")
async def remove_batch_vendor(
    batch_id: str,
    batch_vendor_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Take a vendor out of an OPEN batch - only while none of its stock went in."""
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    batch_vendor = await _get_batch_vendor(db, batch, batch_vendor_id)
    used = (await db.execute(select(ProductBatch.id).where(ProductBatch.batch_vendor_id == batch_vendor.id).limit(1))).first()
    if used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Stock of this vendor was added to the batch - it cannot be removed")
    images = (await db.execute(select(BatchImage).where(BatchImage.batch_vendor_id == batch_vendor.id))).scalars().all()
    public_ids = [i.public_id for i in images]
    for image in images:
        await db.delete(image)
    await db.flush()
    await db.delete(batch_vendor)
    await db.commit()
    await _delete_cloudinary(public_ids)
    await audit_log(db=db, user_id=str(current_user.id), entity="BatchVendor", action="DELETE", entity_id=batch_vendor_id,
                    changes={"batch_vendor_id": batch_vendor_id})
    return await _batch_response(db, batch)


@router.post("/{batch_id}/vendors/{batch_vendor_id}/images")
async def add_images(
    batch_id: str,
    batch_vendor_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    batch_vendor = await _get_batch_vendor(db, batch, batch_vendor_id)
    uploaded = await _upload_images(await _read_images(files))
    try:
        for u in uploaded:
            db.add(BatchImage(batch_id=batch.id, batch_vendor_id=batch_vendor.id, file_url=u["url"], public_id=u["public_id"]))
        await db.commit()
    except Exception:
        await db.rollback()
        await _delete_cloudinary([u["public_id"] for u in uploaded])
        raise
    return await _batch_response(db, batch)


@router.delete("/{batch_id}/images/{image_id}")
async def delete_image(
    batch_id: str,
    image_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    batch = await _get_batch(db, batch_id)
    _require_open(batch)
    image = await db.get(BatchImage, _parse_uuid(image_id, "picture"))
    if not image or image.batch_id != batch.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Picture not found")
    public_id = image.public_id
    await db.delete(image)
    await db.commit()
    await _delete_cloudinary([public_id])
    return await _batch_response(db, batch)
