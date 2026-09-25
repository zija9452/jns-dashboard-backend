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


async def _compute_rush(db: AsyncSession, required_by_date: Optional[date], total_pieces: int):
    """
    Rush is derived, never chosen. Returns (is_rush, rate_snapshot, threshold_snapshot, rush_charge).
    No required_by_date => not rush. Missing rush setting => not rush (never silently charge
    while unable to resolve a real rate).
    """
    if not required_by_date:
        return False, None, None, Decimal("0.00")

    setting = await _get_rush_setting(db)
    if not setting:
        return False, None, None, Decimal("0.00")

    days_until = (required_by_date - date.today()).days
    is_rush = days_until <= setting.threshold_days

    if not is_rush:
        return False, setting.price_per_piece, setting.threshold_days, Decimal("0.00")

    rush_charge = setting.price_per_piece * total_pieces
    return True, setting.price_per_piece, setting.threshold_days, rush_charge


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
        db, quotation_data.required_by_date, total_pieces
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

    is_rush, rate_snapshot, threshold_snapshot, rush_charge = await _compute_rush(
        db, quotation.required_by_date, total_pieces
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


@router.get("/{quotation_id}/pdf")
async def get_quotation_pdf(
    quotation_id: UUID,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    from weasyprint import HTML

    quotation = await _get_quotation_or_404(quotation_id, db)
    items_list = json.loads(quotation.items)
    totals = json.loads(quotation.totals)

    rows_html = ""
    for item in items_list:
        # category_fields holds the selected sub-category options (Neck Style,
        # Sleeves, Fabric, Size Type...) - show them under the item name so the
        # exact customization is visible on the printed quotation, not just stored.
        fields_line = ""
        try:
            fields = json.loads(item.get("category_fields", "{}"))
        except (json.JSONDecodeError, TypeError):
            fields = {}
        if fields:
            fields_line = "<br><span style=\"font-size:10px;color:#6B7280;\">" + " &middot; ".join(
                f"{k}: {v}" for k, v in fields.items()
            ) + "</span>"

        rows_html += f"""
        <tr>
            <td class="border">{item['product_name']}{fields_line}</td>
            <td class="border text-center">{item['quantity']}</td>
            <td class="border text-right">{item['unit_price']:.0f}</td>
            <td class="border text-right">{item['total_price']:.0f}</td>
        </tr>
        """

    rush_row = ""
    if quotation.is_rush and float(quotation.rush_charge) > 0:
        rush_row = f"""
        <tr><td colspan="3" class="text-right"><strong>Rush Order Charge:</strong></td><td class="text-right">{float(quotation.rush_charge):.0f}</td></tr>
        """

    discount_row = ""
    if quotation.discounts and float(quotation.discounts) > 0:
        discount_row = f"""
        <tr><td colspan="3" class="text-right"><strong>Discount:</strong></td><td class="text-right">-{float(quotation.discounts):.0f}</td></tr>
        """

    required_by_line = ""
    if quotation.required_by_date:
        required_by_line = f"<p><strong>Deadline:</strong> {quotation.required_by_date.strftime('%d-%m-%Y')}</p>"

    valid_until_line = ""
    if quotation.valid_until:
        valid_until_line = f"<p><strong>Valid Until:</strong> {quotation.valid_until.strftime('%d-%m-%Y')}</p>"

    rush_badge = '<span style="color:#B91C1C;font-weight:bold;"> [RUSH ORDER]</span>' if quotation.is_rush else ""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 20px; }}
            body {{ font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #111; }}
            h1 {{ text-align: center; margin-bottom: 0; }}
            .subtitle {{ text-align: center; color: #555; margin-top: 4px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ background: #1F2937; color: #fff; padding: 8px; text-align: left; }}
            td {{ padding: 6px 8px; }}
            .border {{ border: 1px solid #999; }}
            .text-right {{ text-align: right; }}
            .text-center {{ text-align: center; }}
            .info {{ margin: 10px 0 20px 0; }}
            .info p {{ margin: 3px 0; }}
        </style>
    </head>
    <body>
        <h1>European Sports Light House</h1>
        <p class="subtitle">QUOTATION — Not a Tax Invoice{rush_badge}</p>

        <div class="info">
            <p><strong>Quotation No:</strong> {quotation.quotation_no} (Rev. {quotation.revision})</p>
            <p><strong>Customer:</strong> {quotation.customer_name or '-'}{' | Team: ' + quotation.team_name if quotation.team_name else ''}</p>
            <p><strong>Date:</strong> {quotation.created_at.strftime('%d-%m-%Y')}</p>
            {required_by_line}
            {valid_until_line}
            <p><strong>Status:</strong> {quotation.status}</p>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Item</th>
                    <th>Qty</th>
                    <th>Rate</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
            <tfoot>
                {discount_row}
                {rush_row}
                <tr><td colspan="3" class="text-right"><strong>Total:</strong></td><td class="text-right"><strong>{totals.get('total', 0):.0f}</strong></td></tr>
            </tfoot>
        </table>

        {f'<p style="margin-top:20px;"><strong>Notes:</strong> {quotation.notes}</p>' if quotation.notes else ''}
    </body>
    </html>
    """

    pdf_bytes = HTML(string=html_content).write_pdf()
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    return {"success": True, "pdf_base64": pdf_base64, "filename": f"{quotation.quotation_no}.pdf"}
