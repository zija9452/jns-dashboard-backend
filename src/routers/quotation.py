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
from ..config.branches import doc_prefix, current_branch_name
from ..models.user import User
from ..models.customer import Customer
from ..models.quotation import (
    Quotation, QuotationCreate, QuotationUpdate, QuotationStatusUpdate,
    QuotationStatus
)
from ..models.customer_invoice import CustomerInvoice, CustomerInvoiceStatus
from ..models.rush_pricing import RushPricingSetting
from ..auth.session_auth import admin_required_from_session
from ..utils.mockup_charges import parse_mockup_charges, mockup_charges_from_totals, load_dye_options
from ..utils.dtf_charges import load_dtf_context, parse_item_dtf, dtf_charges_from_items, dtf_charges_from_totals
from ..utils.item_teams import apply_item_teams, team_names_label, team_groups, has_teams, flat_charges_of_team, flat_charge_label

router = APIRouter(prefix="/quotation", tags=["Quotation"])



def _parse_items(items_json: str, dtf_categories: Optional[set] = None, dtf_setting=None) -> list:
    """dtf_categories / dtf_setting: see utils/dtf_charges.parse_item_dtf."""
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
        dtf = parse_item_dtf(item.get("dtf"), quantity, normalized[-1]["cat_name"], dtf_categories, dtf_setting)
        if dtf:
            normalized[-1]["dtf"] = dtf

    apply_item_teams(items, normalized)
    return normalized, subtotal


async def _get_rush_setting(db: AsyncSession) -> Optional[RushPricingSetting]:
    result = await db.execute(
        select(RushPricingSetting).where(RushPricingSetting.branch == current_branch_name())
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
        statement = select(Quotation.quotation_no).where(
            Quotation.quotation_no.like(doc_prefix("QUO") + "%")
        ).order_by(
            # Numeric max: longer number first, so e.g. QUO-10000 beats QUO-9999
            func.length(Quotation.quotation_no).desc(), Quotation.quotation_no.desc()
        ).limit(1)
        result = await db.execute(statement)
        max_no = result.scalar_one_or_none()

        if max_no:
            parts = max_no.split("-")
            existing_seq = parts[-1] if len(parts) >= 2 else ""
            seq_number = f"{int(existing_seq) + 1:04d}" if existing_seq.isdigit() else "0001"
        else:
            seq_number = "0001"

        quotation_no = f"{doc_prefix('QUO')}{seq_number}"

        counter = 0
        while counter < 100:
            check = await db.execute(select(Quotation.id).where(Quotation.quotation_no == quotation_no).limit(1))
            if check.first():
                seq_number = f"{int(seq_number) + 1:04d}"
                quotation_no = f"{doc_prefix('QUO')}{seq_number}"
                counter += 1
            else:
                break

        if counter >= 100:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate unique quotation number")

        return quotation_no
    finally:
        await db.execute(select(func.pg_advisory_unlock(654321)))


def _build_totals(subtotal: Decimal, discount: Decimal, rush_charge: Decimal,
                  mockup_charges: list, mockup_total: Decimal,
                  dtf_charges: list, dtf_total: Decimal) -> dict:
    total = subtotal - discount + rush_charge + mockup_total + dtf_total
    return {
        "subtotal": float(subtotal),
        "discount": float(discount),
        "rush_charge": float(rush_charge),
        "mockup_charge": float(mockup_total),
        "mockup_charges": mockup_charges,
        "dtf_charge": float(dtf_total),
        "dtf_charges": dtf_charges,
        "tax": 0.0,
        "total": float(total),
    }


async def _build_quotation(
    quotation_data: QuotationCreate, db: AsyncSession, current_user: User,
    quotation_no: Optional[str] = None, revision: int = 1,
) -> tuple[Quotation, dict]:
    """
    A new DRAFT quotation row from the page's data - shared by Create and Revise.
    quotation_no None = next QUO- number; a revision passes the old number and revision + 1.
    Returns (unsaved quotation, extra fields for the response).
    """
    dtf_categories, dtf_setting = await load_dtf_context(db, current_branch_name())
    items_list, subtotal = _parse_items(quotation_data.items, dtf_categories, dtf_setting)
    total_pieces = sum(i["quantity"] for i in items_list)
    discount = quotation_data.discounts or Decimal("0.00")
    mockup_charges, mockup_total = parse_mockup_charges(quotation_data.mockup_charges, items_list, await load_dye_options(db))
    dtf_charges, dtf_total = dtf_charges_from_items(items_list)

    is_rush, rate_snapshot, threshold_snapshot, rush_charge = await _compute_rush(
        db, quotation_data.required_by_date, total_pieces,
        quotation_data.rush_rate_per_piece, quotation_data.rush_threshold_days
    )

    customer_id = quotation_data.customer_id
    if customer_id:
        exists = await db.execute(select(Customer).where(Customer.id == customer_id))
        if not exists.scalar_one_or_none():
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Customer not found")

    if quotation_no is None:
        quotation_no = await _generate_quotation_no(db)
    total_amount = subtotal - discount + rush_charge + mockup_total + dtf_total

    quotation = Quotation(
        quotation_no=quotation_no,
        revision=revision,
        customer_id=customer_id,
        customer_name=quotation_data.customer_name,
        # Items with teams: "Team A, Team B", so the list and search show every team.
        team_name=team_names_label(items_list, quotation_data.team_name),
        salesman_id=quotation_data.salesman_id,
        items=json.dumps(items_list),
        totals=json.dumps(_build_totals(subtotal, discount, rush_charge, mockup_charges, mockup_total, dtf_charges, dtf_total)),
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
    extra = {
        "rush_rate_per_piece": float(rate_snapshot) if rate_snapshot is not None else None,
        "total_pieces": total_pieces,
        "mockup_charge": float(mockup_total),
        "mockup_charges": mockup_charges,
        "dtf_charge": float(dtf_total),
    }
    return quotation, extra


def _saved_response(quotation: Quotation, extra: dict) -> dict:
    return {
        "success": True,
        "quotation_id": str(quotation.id),
        "quotation_no": quotation.quotation_no,
        "revision": quotation.revision,
        "is_rush": quotation.is_rush,
        "rush_charge": float(quotation.rush_charge),
        **extra,
        "total_amount": float(quotation.total_amount),
    }


@router.post("/create")
async def create_quotation(
    quotation_data: QuotationCreate,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    quotation, extra = await _build_quotation(quotation_data, db, current_user)
    db.add(quotation)
    await db.commit()
    await db.refresh(quotation)
    return _saved_response(quotation, extra)


# DRAFT / SENT / REJECTED can be revised; APPROVED and CONVERTED are locked.
REVISABLE_STATUSES = (QuotationStatus.DRAFT, QuotationStatus.SENT, QuotationStatus.REJECTED)


@router.post("/{quotation_id}/revise")
async def revise_quotation(
    quotation_id: UUID,
    quotation_data: QuotationCreate,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Saves the edited quotation as a new revision (same QUO- number, revision + 1, DRAFT).
    The old row becomes REVISED (read-only, PDF only) and points to the new one.
    Locked FOR UPDATE so two people revising at once can't both create a revision.
    """
    result = await db.execute(
        select(Quotation).where(Quotation.id == quotation_id).with_for_update()
    )
    old = result.scalar_one_or_none()
    if not old:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    if old.status == QuotationStatus.REVISED or old.replaced_by_id:
        newer = await db.get(Quotation, old.replaced_by_id) if old.replaced_by_id else None
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"{old.quotation_no} Rev.{old.revision} was already revised"
                   + (f" - open Rev.{newer.revision} instead" if newer else "")
        )
    if old.status not in REVISABLE_STATUSES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"An {old.status.value if hasattr(old.status, 'value') else old.status} quotation can't be revised"
        )

    quotation, extra = await _build_quotation(
        quotation_data, db, current_user, quotation_no=old.quotation_no, revision=old.revision + 1
    )
    db.add(quotation)
    await db.flush()

    old.status_before_revised = old.status.value if hasattr(old.status, "value") else str(old.status)
    old.status = QuotationStatus.REVISED
    old.replaced_by_id = quotation.id
    old.updated_at = datetime.now()
    db.add(old)

    await db.commit()
    await db.refresh(quotation)
    return _saved_response(quotation, extra)


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

    # One row per quotation: its latest revision. Older revisions come with it in
    # "old_revisions" (shown grey under it).
    base = select(Quotation).where(Quotation.replaced_by_id.is_(None))
    if status:
        base = base.where(Quotation.status == status)
    if customer_id:
        base = base.where(Quotation.customer_id == customer_id)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total_count = count_result.scalar_one()

    statement = base.order_by(Quotation.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    quotations = result.scalars().all()

    old_by_no: dict = {}
    numbers = [q.quotation_no for q in quotations if q.revision > 1]
    if numbers:
        old_result = await db.execute(
            select(Quotation)
            .where(Quotation.quotation_no.in_(numbers), Quotation.replaced_by_id.is_not(None))
            .order_by(Quotation.revision.desc())
        )
        for old in old_result.scalars().all():
            old_by_no.setdefault(old.quotation_no, []).append({
                "id": str(old.id),
                "revision": old.revision,
                "total_amount": float(old.total_amount),
                "status": old.status,
                "status_before_revised": old.status_before_revised,
                "created_at": old.created_at.isoformat(),
            })

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
                "old_revisions": old_by_no.get(q.quotation_no, []),
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
        # The page pre-fills a revision with these (rate / window the quotation was saved with)
        "rush_rate_snapshot": float(quotation.rush_rate_snapshot) if quotation.rush_rate_snapshot is not None else None,
        "rush_threshold_snapshot": quotation.rush_threshold_snapshot,
        "valid_until": quotation.valid_until.isoformat() if quotation.valid_until else None,
        "status": quotation.status,
        "revision": quotation.revision,
        "replaced_by_id": str(quotation.replaced_by_id) if quotation.replaced_by_id else None,
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
        # Re-sent DTF blocks keep the rates they were made with (no setting check).
        dtf_categories, _ = await load_dtf_context(db, current_branch_name())
        items_list, subtotal = _parse_items(update_data.items, dtf_categories)
        quotation.items = json.dumps(items_list)
        quotation.team_name = team_names_label(items_list, quotation.team_name)
    else:
        items_list = json.loads(quotation.items)
        subtotal = sum(Decimal(str(i["total_price"])) for i in items_list)

    # Keep the saved mockup charges unless new ones are sent - re-checked against the
    # (possibly changed) items, so a category that now has 5+ pcs can't keep its charge.
    saved_totals = json.loads(quotation.totals) if quotation.totals else {}
    mockup_raw = update_data.mockup_charges if update_data.mockup_charges is not None else mockup_charges_from_totals(saved_totals)
    mockup_charges, mockup_total = parse_mockup_charges(mockup_raw, items_list, await load_dye_options(db))
    dtf_charges, dtf_total = dtf_charges_from_items(items_list)

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
    quotation.totals = json.dumps(_build_totals(subtotal, discount, rush_charge, mockup_charges, mockup_total, dtf_charges, dtf_total))
    quotation.total_amount = subtotal - discount + rush_charge + mockup_total + dtf_total
    # In-place edit - a revision is a separate row now (POST /{id}/revise)
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
    if quotation.status == QuotationStatus.REVISED:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"{quotation.quotation_no} Rev.{quotation.revision} was replaced by a newer revision - use the latest one"
        )

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

    # Deleting a revision re-opens the one it replaced, with the status it had before.
    previous_result = await db.execute(select(Quotation).where(Quotation.replaced_by_id == quotation.id))
    previous = previous_result.scalar_one_or_none()
    if previous:
        previous.replaced_by_id = None
        previous.status = QuotationStatus(previous.status_before_revised or QuotationStatus.DRAFT.value)
        previous.status_before_revised = None
        previous.updated_at = datetime.now()
        db.add(previous)
        await db.flush()

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
        statement = select(CustomerInvoice.invoice_no).where(
            CustomerInvoice.invoice_no.like(doc_prefix("CIN") + "%")
        ).order_by(
            # Numeric max: longer number first, so e.g. CIN-10000 beats CIN-9999
            func.length(CustomerInvoice.invoice_no).desc(), CustomerInvoice.invoice_no.desc()
        ).limit(1)
        result = await db.execute(statement)
        max_invoice_no = result.scalar_one_or_none()

        if max_invoice_no:
            parts = max_invoice_no.split("-")
            existing_seq = parts[-1] if len(parts) >= 2 else ""
            seq_number = f"{int(existing_seq) + 1:04d}" if existing_seq.isdigit() else "0001"
        else:
            seq_number = "0001"

        invoice_no = f"{doc_prefix('CIN')}{seq_number}"
        counter = 0
        while counter < 100:
            check = await db.execute(select(CustomerInvoice).where(CustomerInvoice.invoice_no == invoice_no))
            if check.scalar_one_or_none():
                seq_number = f"{int(seq_number) + 1:04d}"
                invoice_no = f"{doc_prefix('CIN')}{seq_number}"
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
                # DTF logos + the saved roll layout the designer follows
                **({"dtf": i["dtf"]} if i.get("dtf") else {}),
                # Team of the item and the row it was added "+ Similar" from
                **({"team": i["team"]} if i.get("team") else {}),
                **({"similar_of": i["similar_of"]} if i.get("similar_of") else {}),
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
                "mockup_charge": totals.get("mockup_charge", 0.0),
                "mockup_charges": mockup_charges_from_totals(totals),
                "dtf_charge": totals.get("dtf_charge", 0.0),
                "dtf_charges": dtf_charges_from_totals(totals),
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
            # Nothing has been paid yet, so no real payment mode - "credit" (udhaar) is
            # what an unpaid order is. The actual mode is recorded with each payment.
            payment_method="credit",
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

    def item_row(idx, item) -> str:
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
        dtf = item.get("dtf")
        if dtf:
            logos = ", ".join(f'{l["w"]:g}&times;{l["h"]:g}"' for l in dtf.get("logos", []))
            chips += f'<span class="chip"><b>DTF:</b> {logos} &middot; {dtf.get("half_meters", 0) / 2:g} m roll</span>'
        desc = escape(str(item.get("custom_description") or ""))
        # A "+ Similar" row sits right under its first row, marked with an arrow.
        similar = item.get("similar_of")
        return f"""
        <tr{' class="similar"' if similar else ''}>
            <td class="c">{idx}</td>
            <td>
                <div class="item-name">{'<span class="arrow">&#8627;</span>' if similar else ''}{escape(str(item.get('product_name', '')))}</div>
                {f'<div class="item-desc">{desc}</div>' if desc else ''}
                {f'<div class="chips">{chips}</div>' if chips else ''}
            </td>
            <td class="c">{int(item.get('quantity', 0))}</td>
            <td class="r">{money(item.get('unit_price'))}</td>
            <td class="r strong">{money(item.get('total_price'))}</td>
        </tr>"""

    saved_mockups = mockup_charges_from_totals(totals)
    team_order = has_teams(items_list)
    rows_html = ""
    team_totals = []  # (team, pieces, total, flat charges) for the totals box
    if team_order:
        # One block per team: heading, its items, its flat charges and DTF, its total.
        for team, rows in team_groups(items_list, quotation.team_name):
            pieces = sum(int(item.get("quantity", 0)) for _, item in rows)
            flats = flat_charges_of_team(saved_mockups, team)
            flat_total = sum(float(mc.get("amount", 0)) for mc in flats)
            dtf_total = sum(float((item.get("dtf") or {}).get("amount", 0) or 0) for _, item in rows)
            team_total = sum(float(item.get("total_price", 0)) for _, item in rows) + flat_total + dtf_total
            team_totals.append((team, pieces, team_total, flat_total))
            rows_html += f'<tr class="team-head"><td colspan="5">{escape(team)}</td></tr>'
            rows_html += "".join(item_row(idx, item) for idx, item in rows)
            for mc in flats:
                rows_html += (
                    f'<tr class="extra flat"><td></td><td>MOQ Charges - {escape(str(mc.get("category", "")))}'
                    f'<div class="item-desc">{int(mc.get("pieces", 0))} pcs (under 5) in this team &middot; once, not per piece</div></td>'
                    f'<td></td><td></td><td class="r strong">{money(mc.get("amount"))}</td></tr>'
                )
            for idx, item in rows:
                dtf = item.get("dtf") or {}
                if dtf.get("amount"):
                    rows_html += (
                        f'<tr class="extra dtf"><td></td><td>DTF Printing - {escape(str(item.get("product_name", "")))}'
                        f'<div class="item-desc">item {idx} &middot; {float(dtf.get("half_meters", 0)) / 2:g} m roll</div></td>'
                        f'<td></td><td></td><td class="r strong">{money(dtf.get("amount"))}</td></tr>'
                    )
            rows_html += (
                f'<tr class="team-total"><td></td><td>{escape(team)} total</td>'
                f'<td class="c">{pieces}</td><td></td><td class="r">{money(team_total)}</td></tr>'
            )
    else:
        rows_html = "".join(item_row(idx, item) for idx, item in enumerate(items_list, 1))

    subtotal = totals.get("subtotal", sum(float(i.get("total_price", 0)) for i in items_list))
    if team_totals:
        # Team order: Subtotal is just a heading, each team's total under it.
        total_rows = f'<tr><td colspan="2" class="strong">Subtotal ({total_pieces} pcs)</td></tr>'
        for team, pieces, team_total, _flat_total in team_totals:
            total_rows += (
                f'<tr class="team"><td style="padding-left:20px;">{escape(team)} ({pieces} pcs)</td>'
                f'<td class="r">{money(team_total)}</td></tr>'
            )
    else:
        total_rows = f'<tr><td>Subtotal ({total_pieces} pcs)</td><td class="r">{money(subtotal)}</td></tr>'
    if quotation.discounts and float(quotation.discounts) > 0:
        total_rows += f'<tr><td>Discount</td><td class="r">- {money(quotation.discounts)}</td></tr>'
    if quotation.is_rush and float(quotation.rush_charge) > 0:
        rate = quotation.rush_rate_snapshot
        rush_detail = (
            f'<div class="sub">Rs. {money(rate)} per piece &times; {total_pieces} pcs</div>' if rate is not None else ""
        )
        total_rows += f'<tr class="rush"><td>Rush Charge{rush_detail}</td><td class="r">+ {money(quotation.rush_charge)}</td></tr>'
    # A team order shows its flat charges and DTF inside each team's block (and in the
    # team totals above), so they are not listed again here.
    for mc in ([] if team_order else saved_mockups):
        total_rows += (
            f'<tr><td>MOQ Charges - {flat_charge_label(mc)}'
            f'<div class="sub" style="color:#6B7280;">{int(mc.get("pieces", 0))} pcs (under 5) &middot; once for this item</div></td>'
            f'<td class="r">+ {money(mc.get("amount"))}</td></tr>'
        )
    for dc in ([] if team_order else dtf_charges_from_totals(totals)):
        total_rows += (
            f'<tr><td>DTF Printing - {escape(str(dc.get("category", "")))}'
            f'<div class="sub" style="color:#6B7280;">item {int(dc.get("line", 0))} &middot; {float(dc.get("meters", 0)):g} m roll</div></td>'
            f'<td class="r">+ {money(dc.get("amount"))}</td></tr>'
        )

    status = getattr(quotation.status, "value", quotation.status)
    rush_badge = '<span class="badge badge-rush">RUSH ORDER</span>' if quotation.is_rush else ""
    logo = _quotation_logo_data_uri()
    logo_html = f'<img class="logo" src="{logo}">' if logo else ""
    shop_name = escape(current_branch_name())
    team_word = "Teams" if len(team_totals) > 1 else "Team"
    team = f'<div class="muted">{team_word}: <b>{escape(quotation.team_name)}</b></div>' if quotation.team_name else ""
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
        @bottom-left {{ content: "{shop_name}  |  {escape(quotation.quotation_no)}"; font-size: 8px; color: #6B7280; }}
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
    .arrow {{ color: #6B7280; margin-right: 4px; }}
    .items tr.similar td:nth-child(2) {{ padding-left: 20px; }}
    .items tr.team-head td {{ background: #FFD01F !important; font-size: 11.5px; font-weight: 800; letter-spacing: 0.5px;
                              text-transform: uppercase; border: 1px solid #111827; }}
    .items tr.extra.dtf td {{ background: #F0FDFA !important; color: #0F766E; }}
    .items tr.team-total td {{ background: #FFFBEB !important; font-weight: 800; border-bottom: 1.5px solid #111827; }}
    .totals tr.team td {{ color: #374151; }}

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
            <div class="company">{shop_name}</div>
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

    <div class="thanks">Thank you for choosing {shop_name}.</div>
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
