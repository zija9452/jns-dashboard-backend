from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID
import uuid
import json
import base64

from ..database.database import get_db
from ..models.user import User
from ..models.customer import Customer
from ..models.quotation import (
    Quotation, QuotationCreate, QuotationUpdate, QuotationStatusUpdate,
    QuotationStatus
)
from ..models.customer_invoice import CustomerInvoice, CustomerInvoiceStatus
from ..models.rush_pricing import RushPricingSetting
from ..auth.session_auth import admin_required_from_session

router = APIRouter(prefix="/quotation", tags=["Quotation"])

DEFAULT_BRANCH = "European Sports Light House"


def _parse_items(items_json: str) -> list:
    try:
        items = json.loads(items_json)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid items JSON")
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Quotation must have at least one item")

    normalized = []
    subtotal = Decimal("0")
    for item in items:
        pro_name = item.get("pro_name") or item.get("product_name")
        if not pro_name:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Product name is required for each item")

        try:
            quantity = int(item.get("pro_quantity", item.get("quantity", 0)))
        except (TypeError, ValueError):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid quantity")
        if quantity <= 0:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Quantity must be positive")

        try:
            unit_price = float(item.get("unit_price", 0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid unit price")
        if unit_price < 0:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Unit price cannot be negative")

        item_total = quantity * unit_price
        subtotal += Decimal(str(item_total))

        normalized.append({
            "product_name": str(pro_name),
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": item_total,
            "cat_name": str(item.get("cat_name", "")),
            "category_fields": item.get("category_fields", "{}"),
            "custom_description": str(item.get("custom_description", "")),
            "imgfile": str(item.get("imgfile", "")),
            "imgfile2": str(item.get("imgfile2", "")),
            "imgfile3": str(item.get("imgfile3", "")),
        })

    return normalized, subtotal


async def _get_rush_setting(db: AsyncSession) -> Optional[RushPricingSetting]:
    result = await db.execute(
        select(RushPricingSetting).where(RushPricingSetting.branch == DEFAULT_BRANCH)
    )
    return result.scalar_one_or_none()


async def _compute_rush(
    db: AsyncSession,
    required_by_date: Optional[date],
    total_pieces: int,
    rate_override: Optional[Decimal] = None,
    threshold_override: Optional[int] = None,
):
    """
    Rush is derived from the deadline, never chosen. Returns (is_rush, rate_snapshot,
    threshold_snapshot, rush_charge). rate_override is the per-piece rush rate the
    cashier entered (editable, pre-filled with the default); threshold_override is the
    rush window the page used. Either one missing falls back to the DB rush setting.
    No required_by_date, or no rate/threshold resolvable at all => not rush.
    """
    if not required_by_date:
        return False, None, None, Decimal("0.00")

    setting = None
    if rate_override is None or threshold_override is None:
        setting = await _get_rush_setting(db)
    rate = rate_override if rate_override is not None else (setting.price_per_piece if setting else None)
    threshold = threshold_override if threshold_override is not None else (setting.threshold_days if setting else None)
    if rate is None or threshold is None:
        return False, None, None, Decimal("0.00")
    if rate < 0:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Rush rate cannot be negative")

    days_until = (required_by_date - date.today()).days
    is_rush = days_until <= threshold

    if not is_rush:
        return False, rate, threshold, Decimal("0.00")

    rush_charge = Decimal(str(rate)) * total_pieces
    return True, rate, threshold, rush_charge


async def _generate_quotation_no(db: AsyncSession) -> str:
    lock_statement = select(func.pg_advisory_lock(654321))
    await db.execute(lock_statement)
    try:
        statement = select(func.max(Quotation.quotation_no)).where(Quotation.quotation_no.like("QUO-%"))
        result = await db.execute(statement)
        max_no = result.scalar_one_or_none()

        if max_no:
            parts = max_no.split("-")
            existing_seq = parts[-1] if len(parts) >= 2 else ""
            seq_number = f"{int(existing_seq) + 1:04d}" if existing_seq.isdigit() else "0001"
        else:
            seq_number = "0001"

        quotation_no = f"QUO-{seq_number}"

        counter = 0
        while counter < 100:
            check = await db.execute(select(Quotation).where(Quotation.quotation_no == quotation_no))
            if check.scalar_one_or_none():
                seq_number = f"{int(seq_number) + 1:04d}"
                quotation_no = f"QUO-{seq_number}"
                counter += 1
            else:
                break

        if counter >= 100:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate unique quotation number")

        return quotation_no
    finally:
        await db.execute(select(func.pg_advisory_unlock(654321)))


def _build_totals(subtotal: Decimal, discount: Decimal, rush_charge: Decimal) -> dict:
    total = subtotal - discount + rush_charge
    return {
        "subtotal": float(subtotal),
        "discount": float(discount),
        "rush_charge": float(rush_charge),
        "tax": 0.0,
        "total": float(total),
    }


@router.post("/create")
async def create_quotation(
    quotation_data: QuotationCreate,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    items_list, subtotal = _parse_items(quotation_data.items)
    total_pieces = sum(i["quantity"] for i in items_list)
    discount = quotation_data.discounts or Decimal("0.00")

    is_rush, rate_snapshot, threshold_snapshot, rush_charge = await _compute_rush(
        db, quotation_data.required_by_date, total_pieces,
        quotation_data.rush_rate_per_piece, quotation_data.rush_threshold_days
    )

    customer_id = quotation_data.customer_id
    if customer_id:
        exists = await db.execute(select(Customer).where(Customer.id == customer_id))
        if not exists.scalar_one_or_none():
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Customer not found")

    quotation_no = await _generate_quotation_no(db)
    total_amount = subtotal - discount + rush_charge

    quotation = Quotation(
        quotation_no=quotation_no,
        customer_id=customer_id,
        customer_name=quotation_data.customer_name,
        team_name=quotation_data.team_name,
        salesman_id=quotation_data.salesman_id,
        items=json.dumps(items_list),
        totals=json.dumps(_build_totals(subtotal, discount, rush_charge)),
        total_amount=total_amount,
        taxes=Decimal("0.00"),
        discounts=discount,
        required_by_date=quotation_data.required_by_date,
        is_rush=is_rush,
        rush_rate_snapshot=rate_snapshot,
        rush_threshold_snapshot=threshold_snapshot,
        rush_charge=rush_charge,
        valid_until=quotation_data.valid_until,
        status=QuotationStatus.DRAFT,
        notes=quotation_data.notes,
        created_by=current_user.id,
    )

    db.add(quotation)
    await db.commit()
    await db.refresh(quotation)

    return {
        "success": True,
        "quotation_id": str(quotation.id),
        "quotation_no": quotation.quotation_no,
        "is_rush": quotation.is_rush,
        "rush_charge": float(quotation.rush_charge),
        "rush_rate_per_piece": float(rate_snapshot) if rate_snapshot is not None else None,
        "total_pieces": total_pieces,
        "total_amount": float(quotation.total_amount),
    }


@router.get("/list")
async def list_quotations(
    page: int = 1,
    limit: int = 50,
    status: Optional[QuotationStatus] = None,
    customer_id: Optional[UUID] = None,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * limit

    base = select(Quotation)
    if status:
        base = base.where(Quotation.status == status)
    if customer_id:
        base = base.where(Quotation.customer_id == customer_id)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total_count = count_result.scalar_one()

    statement = base.order_by(Quotation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    quotations = result.scalars().all()

    return {
        "data": [
            {
                "id": str(q.id),
                "quotation_no": q.quotation_no,
                "customer_name": q.customer_name,
                "team_name": q.team_name,
                "total_amount": float(q.total_amount),
                "discounts": float(q.discounts or 0),
                "is_rush": q.is_rush,
                "required_by_date": q.required_by_date.isoformat() if q.required_by_date else None,
                "valid_until": q.valid_until.isoformat() if q.valid_until else None,
                "status": q.status,
                "revision": q.revision,
                "converted_invoice_id": str(q.converted_invoice_id) if q.converted_invoice_id else None,
                "created_at": q.created_at.isoformat(),
            }
            for q in quotations
        ],
        "page": page,
        "limit": limit,
        "total": total_count,
        "totalPages": (total_count + limit - 1) // limit if limit > 0 else 1,
    }


async def _get_quotation_or_404(quotation_id: UUID, db: AsyncSession) -> Quotation:
    result = await db.execute(select(Quotation).where(Quotation.id == quotation_id))
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    return quotation


@router.get("/{quotation_id}")
async def get_quotation(
    quotation_id: UUID,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    quotation = await _get_quotation_or_404(quotation_id, db)
    return {
        "id": str(quotation.id),
        "quotation_no": quotation.quotation_no,
        "customer_id": str(quotation.customer_id) if quotation.customer_id else None,
        "customer_name": quotation.customer_name,
        "team_name": quotation.team_name,
        "salesman_id": str(quotation.salesman_id) if quotation.salesman_id else None,
        "items": json.loads(quotation.items),
        "totals": json.loads(quotation.totals),
        "total_amount": float(quotation.total_amount),
        "discounts": float(quotation.discounts or 0),
        "required_by_date": quotation.required_by_date.isoformat() if quotation.required_by_date else None,
        "is_rush": quotation.is_rush,
        "rush_charge": float(quotation.rush_charge),
        "valid_until": quotation.valid_until.isoformat() if quotation.valid_until else None,
        "status": quotation.status,
        "revision": quotation.revision,
        "notes": quotation.notes,
        "converted_invoice_id": str(quotation.converted_invoice_id) if quotation.converted_invoice_id else None,
        "created_at": quotation.created_at.isoformat(),
        "updated_at": quotation.updated_at.isoformat(),
    }


@router.put("/{quotation_id}")
async def update_quotation(
    quotation_id: UUID,
    update_data: QuotationUpdate,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    quotation = await _get_quotation_or_404(quotation_id, db)

    if quotation.status not in (QuotationStatus.DRAFT, QuotationStatus.SENT):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit a quotation that is {quotation.status} — only DRAFT or SENT quotations can be edited"
        )

    if update_data.items is not None:
        items_list, subtotal = _parse_items(update_data.items)
        quotation.items = json.dumps(items_list)
    else:
        items_list = json.loads(quotation.items)
        subtotal = sum(Decimal(str(i["total_price"])) for i in items_list)

    if update_data.required_by_date is not None:
        quotation.required_by_date = update_data.required_by_date
    if update_data.valid_until is not None:
        quotation.valid_until = update_data.valid_until
    if update_data.notes is not None:
        quotation.notes = update_data.notes

    discount = update_data.discounts if update_data.discounts is not None else (quotation.discounts or Decimal("0.00"))
    total_pieces = sum(i["quantity"] for i in items_list)

    # Keep the rate/threshold this quotation was saved with unless new ones are sent,
    # so editing never silently switches to a different default rush rate.
    rate_override = update_data.rush_rate_per_piece if update_data.rush_rate_per_piece is not None else quotation.rush_rate_snapshot
    threshold_override = update_data.rush_threshold_days if update_data.rush_threshold_days is not None else quotation.rush_threshold_snapshot
    is_rush, rate_snapshot, threshold_snapshot, rush_charge = await _compute_rush(
        db, quotation.required_by_date, total_pieces, rate_override, threshold_override
    )

    quotation.discounts = discount
    quotation.is_rush = is_rush
    quotation.rush_rate_snapshot = rate_snapshot
    quotation.rush_threshold_snapshot = threshold_snapshot
    quotation.rush_charge = rush_charge
    quotation.totals = json.dumps(_build_totals(subtotal, discount, rush_charge))
    quotation.total_amount = subtotal - discount + rush_charge
    quotation.revision += 1
    quotation.updated_at = datetime.now()

    db.add(quotation)
    await db.commit()
    await db.refresh(quotation)

    return {"success": True, "quotation_id": str(quotation.id), "revision": quotation.revision}


@router.post("/{quotation_id}/status")
async def update_quotation_status(
    quotation_id: UUID,
    status_update: QuotationStatusUpdate,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    quotation = await _get_quotation_or_404(quotation_id, db)

    if quotation.status == QuotationStatus.CONVERTED:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Quotation already converted to an order")

    allowed_transitions = {
        QuotationStatus.DRAFT: {QuotationStatus.SENT, QuotationStatus.REJECTED},
        QuotationStatus.SENT: {QuotationStatus.APPROVED, QuotationStatus.REJECTED, QuotationStatus.DRAFT},
        QuotationStatus.APPROVED: {QuotationStatus.REJECTED},
        QuotationStatus.REJECTED: {QuotationStatus.DRAFT},
    }

    if status_update.status not in allowed_transitions.get(quotation.status, set()):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move quotation from {quotation.status} to {status_update.status}"
        )

    quotation.status = status_update.status
    quotation.updated_at = datetime.now()
    db.add(quotation)
    await db.commit()
    await db.refresh(quotation)

    return {"success": True, "status": quotation.status}


@router.delete("/{quotation_id}")
async def delete_quotation(
    quotation_id: UUID,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    quotation = await _get_quotation_or_404(quotation_id, db)

    if quotation.status != QuotationStatus.DRAFT:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Only DRAFT quotations can be deleted")

    await db.delete(quotation)
    await db.commit()

    return {"message": "Quotation deleted successfully"}


@router.post("/{quotation_id}/convert")
async def convert_quotation_to_order(
    quotation_id: UUID,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    quotation = await _get_quotation_or_404(quotation_id, db)

    if quotation.status != QuotationStatus.APPROVED:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Only an APPROVED quotation can be converted to an order"
        )

    # CustomerInvoice.customer_id is NOT NULL - without this check, a customer-less
    # quotation (old test rows created before Customer became required on Quotation)
    # would crash here instead of failing with a clear message.
    if not quotation.customer_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Customer required to convert to an order"
        )

    items_list = json.loads(quotation.items)
    totals = json.loads(quotation.totals)

    # Reuse the same CIN- numbering pattern/lock as SaveCustomerOrders
    lock_statement = select(func.pg_advisory_lock(123456))
    await db.execute(lock_statement)
    try:
        statement = select(func.max(CustomerInvoice.invoice_no)).where(CustomerInvoice.invoice_no.like("CIN-%"))
        result = await db.execute(statement)
        max_invoice_no = result.scalar_one_or_none()

        if max_invoice_no:
            parts = max_invoice_no.split("-")
            existing_seq = parts[-1] if len(parts) >= 2 else ""
            seq_number = f"{int(existing_seq) + 1:04d}" if existing_seq.isdigit() else "0001"
        else:
            seq_number = "0001"

        invoice_no = f"CIN-{seq_number}"
        counter = 0
        while counter < 100:
            check = await db.execute(select(CustomerInvoice).where(CustomerInvoice.invoice_no == invoice_no))
            if check.scalar_one_or_none():
                seq_number = f"{int(seq_number) + 1:04d}"
                invoice_no = f"CIN-{seq_number}"
                counter += 1
            else:
                break

        if counter >= 100:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate unique invoice number")

        invoice_items = [
            {
                "product_name": i["product_name"],
                "quantity": i["quantity"],
                "unit_price": i["unit_price"],
                "subtotal": i["quantity"] * i["unit_price"],
                "discount": 0,
                "total_price": i["total_price"],
                "cat_name": i.get("cat_name", ""),
                "category_fields": i.get("category_fields", "{}"),
                "custom_description": i.get("custom_description", ""),
                "imgfile": i.get("imgfile", ""),
                "imgfile2": i.get("imgfile2", ""),
                "imgfile3": i.get("imgfile3", ""),
            }
            for i in items_list
        ]

        invoice = CustomerInvoice(
            id=uuid.uuid4(),
            invoice_no=invoice_no,
            customer_id=quotation.customer_id,
            customer_name=quotation.customer_name,
            team_name=quotation.team_name,
            salesman_id=quotation.salesman_id,
            items=json.dumps(invoice_items),
            totals=json.dumps({
                "subtotal": totals.get("subtotal", 0.0),
                "tax": 0.0,
                "discount": totals.get("discount", 0.0),
                "rush_charge": totals.get("rush_charge", 0.0),
                "total": float(quotation.total_amount),
                "amount_paid": 0.0,
                "balance_due": float(quotation.total_amount),
                "payment_status": "unpaid",
            }),
            total_amount=quotation.total_amount,
            amount_paid=Decimal("0.00"),
            balance_due=quotation.total_amount,
            payment_status="unpaid",
            payments_history="[]",
            taxes=Decimal("0.00"),
            discounts=quotation.discounts,
            required_by_date=quotation.required_by_date,
            is_rush=quotation.is_rush,
            rush_rate_snapshot=quotation.rush_rate_snapshot,
            rush_threshold_snapshot=quotation.rush_threshold_snapshot,
            rush_charge=quotation.rush_charge,
            status=CustomerInvoiceStatus.PENDING,
            payment_method="cash",
            notes=f"Converted from quotation {quotation.quotation_no}" + (f" | {quotation.notes}" if quotation.notes else ""),
            created_by=current_user.id,
        )

        db.add(invoice)
        await db.flush()

        quotation.status = QuotationStatus.CONVERTED
        quotation.converted_invoice_id = invoice.id
        quotation.updated_at = datetime.now()
        db.add(quotation)

        await db.commit()
        await db.refresh(invoice)

        return {
            "success": True,
            "invoice_id": str(invoice.id),
            "invoice_no": invoice.invoice_no,
            "quotation_id": str(quotation.id),
        }
    finally:
        await db.execute(select(func.pg_advisory_unlock(123456)))



def _quotation_logo_data_uri() -> str:
    """European Sports logo (backend/Images) as a data URI, or '' if missing."""
    import os
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Images", "european-logo-blk.svg"
    )
    try:
        with open(logo_path, "rb") as f:
            return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode("ascii")
    except OSError:
        return ""


def _build_quotation_pdf_html(quotation: Quotation) -> str:
    """A4 quotation document: branded header, bordered item table, totals box, terms."""
    from html import escape

    items_list = json.loads(quotation.items)
    totals = json.loads(quotation.totals)
    total_pieces = sum(int(i.get("quantity", 0)) for i in items_list)

    def money(v) -> str:
        return f"{float(v or 0):,.0f}"

    def fmt_date(d) -> str:
        return d.strftime("%d %b %Y") if d else "-"

    rows_html = ""
    for idx, item in enumerate(items_list, 1):
        # category_fields holds the selected sub-category options (Neck Style,
        # Sleeves, Fabric, Size Type...) - shown as small chips under the item name so
        # the exact customization is visible on the printed quotation.
        try:
            fields = json.loads(item.get("category_fields", "{}") or "{}")
        except (json.JSONDecodeError, TypeError):
            fields = {}
        chips = "".join(
            f'<span class="chip"><b>{escape(str(k))}:</b> {escape(str(v))}</span>'
            for k, v in fields.items() if v not in (None, "")
        )
        desc = escape(str(item.get("custom_description") or ""))
        rows_html += f"""
        <tr>
            <td class="c">{idx}</td>
            <td>
                <div class="item-name">{escape(str(item.get('product_name', '')))}</div>
                {f'<div class="item-desc">{desc}</div>' if desc else ''}
                {f'<div class="chips">{chips}</div>' if chips else ''}
            </td>
            <td class="c">{int(item.get('quantity', 0))}</td>
            <td class="r">{money(item.get('unit_price'))}</td>
            <td class="r strong">{money(item.get('total_price'))}</td>
        </tr>"""

    subtotal = totals.get("subtotal", sum(float(i.get("total_price", 0)) for i in items_list))
    total_rows = f'<tr><td>Subtotal ({total_pieces} pcs)</td><td class="r">{money(subtotal)}</td></tr>'
    if quotation.discounts and float(quotation.discounts) > 0:
        total_rows += f'<tr><td>Discount</td><td class="r">- {money(quotation.discounts)}</td></tr>'
    if quotation.is_rush and float(quotation.rush_charge) > 0:
        rate = quotation.rush_rate_snapshot
        rush_detail = (
            f'<div class="sub">Rs. {money(rate)} per piece &times; {total_pieces} pcs</div>' if rate is not None else ""
        )
        total_rows += f'<tr class="rush"><td>Rush Charge{rush_detail}</td><td class="r">+ {money(quotation.rush_charge)}</td></tr>'

    status = getattr(quotation.status, "value", quotation.status)
    rush_badge = '<span class="badge badge-rush">RUSH ORDER</span>' if quotation.is_rush else ""
    logo = _quotation_logo_data_uri()
    logo_html = f'<img class="logo" src="{logo}">' if logo else ""
    team = f'<div class="muted">Team: <b>{escape(quotation.team_name)}</b></div>' if quotation.team_name else ""
    notes_html = (
        f'<div class="notes"><div class="label">Notes</div>{escape(quotation.notes)}</div>' if quotation.notes else ""
    )
    deadline_row = (
        f'<tr class="deadline"><td>Deadline</td><td>{fmt_date(quotation.required_by_date)}</td></tr>'
        if quotation.required_by_date else ""
    )
    valid_row = (
        f'<tr><td>Valid Until</td><td>{fmt_date(quotation.valid_until)}</td></tr>' if quotation.valid_until else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    @page {{
        size: A4;
        margin: 14mm 12mm 18mm 12mm;
        @bottom-left {{ content: "European Sports Light House  |  {escape(quotation.quotation_no)}"; font-size: 8px; color: #6B7280; }}
        @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font-size: 8px; color: #6B7280; }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: "Helvetica Neue", Arial, Helvetica, sans-serif; font-size: 10.5px; color: #111827; margin: 0; }}
    .sheet {{ border: 1.5px solid #111827; }}
    .accent {{ height: 6px; background: #FFD01F; border-bottom: 1.5px solid #111827; }}

    .header {{ display: table; width: 100%; padding: 14px 16px; border-bottom: 1.5px solid #111827; }}
    .header > div {{ display: table-cell; vertical-align: middle; }}
    .brand {{ width: 60%; }}
    .logo {{ height: 52px; float: left; margin-right: 12px; }}
    .company {{ font-size: 18px; font-weight: 800; letter-spacing: 0.3px; padding-top: 8px; }}
    .tagline {{ color: #6B7280; font-size: 9.5px; margin-top: 2px; }}
    .doc {{ text-align: right; }}
    .doc-title {{ font-size: 24px; font-weight: 800; letter-spacing: 3px; }}
    .doc-sub {{ font-size: 9px; color: #6B7280; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }}
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 9px; font-weight: 700; letter-spacing: 0.8px; margin-top: 6px; }}
    .badge-rush {{ background: #FFEDD5; color: #C2410C; border: 1px solid #EA580C; }}
    .badge-status {{ background: #F3F4F6; color: #374151; border: 1px solid #9CA3AF; margin-left: 4px; }}

    .info {{ display: table; width: 100%; border-bottom: 1.5px solid #111827; }}
    .info > div {{ display: table-cell; width: 50%; padding: 10px 16px; vertical-align: top; }}
    .info > div + div {{ border-left: 1px solid #D1D5DB; }}
    .label {{ font-size: 8.5px; font-weight: 700; color: #6B7280; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
    .cust {{ font-size: 13px; font-weight: 700; margin-bottom: 2px; }}
    .muted {{ color: #4B5563; }}
    .meta {{ width: 100%; border-collapse: collapse; }}
    .meta td {{ padding: 2px 0; }}
    .meta td:first-child {{ color: #6B7280; width: 45%; }}
    .meta td:last-child {{ font-weight: 600; text-align: right; }}
    .meta .deadline td:last-child {{ color: #C2410C; }}

    .items {{ width: 100%; border-collapse: collapse; }}
    .items thead {{ display: table-header-group; }}
    .items th {{ background: #111827; color: #fff; font-size: 9px; text-transform: uppercase; letter-spacing: 0.8px;
                 padding: 8px 8px; border: 1px solid #111827; text-align: left; }}
    .items td {{ padding: 8px; border: 1px solid #D1D5DB; vertical-align: top; }}
    .items tbody tr:nth-child(even) td {{ background: #F9FAFB; }}
    .items tr {{ page-break-inside: avoid; }}
    .items th.c, .items td.c {{ text-align: center; }}
    .items th.r, .items td.r {{ text-align: right; }}
    .strong {{ font-weight: 700; }}
    .item-name {{ font-weight: 700; font-size: 11px; }}
    .item-desc {{ color: #4B5563; margin-top: 2px; }}
    .chips {{ margin-top: 4px; }}
    .chip {{ display: inline-block; border: 1px solid #E5E7EB; background: #fff; border-radius: 3px;
             padding: 1px 5px; margin: 2px 3px 0 0; font-size: 8.5px; color: #374151; }}
    .chip b {{ color: #6B7280; font-weight: 600; }}

    .bottom {{ display: table; width: 100%; border-top: 1.5px solid #111827; page-break-inside: avoid; }}
    .bottom > div {{ display: table-cell; vertical-align: top; padding: 12px 16px; }}
    .side {{ width: 55%; }}
    .notes {{ color: #374151; }}
    .totals {{ width: 100%; border-collapse: collapse; border: 1px solid #111827; }}
    .totals td {{ padding: 6px 10px; border-bottom: 1px solid #E5E7EB; }}
    .totals td.r {{ text-align: right; font-weight: 600; white-space: nowrap; }}
    .totals .sub {{ font-size: 8.5px; color: #C2410C; font-weight: 400; margin-top: 1px; }}
    .totals .rush td {{ color: #C2410C; }}
    .totals .grand td {{ background: #111827; color: #fff; font-size: 13px; font-weight: 800; border-bottom: none; }}
    .totals .grand td.r {{ color: #FFD01F; }}

    .thanks {{ text-align: center; font-size: 9.5px; color: #374151; padding: 8px; border-top: 1.5px solid #111827; background: #FFFBEB; }}
</style>
</head>
<body>
<div class="sheet">
    <div class="accent"></div>
    <div class="header">
        <div class="brand">
            {logo_html}
            <div class="company">European Sports Light House</div>
            <div class="tagline">Custom Sportswear &amp; Team Kits</div>
        </div>
        <div class="doc">
            <div class="doc-title">QUOTATION</div>
            <div class="doc-sub">Not a Tax Invoice</div>
            {rush_badge}<span class="badge badge-status">{escape(str(status))}</span>
        </div>
    </div>

    <div class="info">
        <div>
            <div class="label">Quotation For</div>
            <div class="cust">{escape(quotation.customer_name or '-')}</div>
            {team}
        </div>
        <div>
            <div class="label">Quotation Details</div>
            <table class="meta">
                <tr><td>Quotation No</td><td>{escape(quotation.quotation_no)} (Rev. {quotation.revision})</td></tr>
                <tr><td>Date</td><td>{fmt_date(quotation.created_at)}</td></tr>
                {deadline_row}
                {valid_row}
            </table>
        </div>
    </div>

    <table class="items">
        <thead>
            <tr>
                <th class="c" style="width:6%;">#</th>
                <th style="width:52%;">Item &amp; Specifications</th>
                <th class="c" style="width:10%;">Qty</th>
                <th class="r" style="width:14%;">Rate (Rs.)</th>
                <th class="r" style="width:18%;">Amount (Rs.)</th>
            </tr>
        </thead>
        <tbody>{rows_html}
        </tbody>
    </table>

    <div class="bottom">
        <div class="side">{notes_html}</div>
        <div>
            <table class="totals">
                {total_rows}
                <tr class="grand"><td>Grand Total</td><td class="r">Rs. {money(totals.get('total', quotation.total_amount))}</td></tr>
            </table>
        </div>
    </div>

    <div class="thanks">Thank you for choosing European Sports Light House.</div>
</div>
</body>
</html>"""


@router.get("/{quotation_id}/pdf")
async def get_quotation_pdf(
    quotation_id: UUID,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    from weasyprint import HTML

    quotation = await _get_quotation_or_404(quotation_id, db)
    html_content = _build_quotation_pdf_html(quotation)

    pdf_bytes = HTML(string=html_content).write_pdf()
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    return {"success": True, "pdf_base64": pdf_base64, "filename": f"{quotation.quotation_no}.pdf"}
