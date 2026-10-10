"""
Payment proofs: screenshots of online payments (Easypaisa / bank) of customized
invoices, and the combined Payments Record list (bank deposits + payment proofs).

Flow: online payment recorded -> proof MISSING (payment already counts as paid)
-> pay slip attached -> PENDING -> sales/admin APPROVED (locked)
or REJECTED with a reason (the invoice is not changed) -> a new pay slip is attached
-> PENDING again (same as a rejected cash deposit being resubmitted).
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, literal, union_all, cast, Date
from typing import List, Optional
from uuid import UUID
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
import json
import logging
import uuid

from ..database.database import get_db
from ..models.user import User
from ..models.cash_deposit import CashDeposit
from ..models.payment_proof import (
    PaymentProof, PaymentProofImage, PaymentProofReject, is_online_method,
    PROOF_MISSING, PROOF_PENDING, PROOF_APPROVED, PROOF_REJECTED, SOURCE_CUSTOMIZED,
)
from ..services.cloudinary_service import CloudinaryService
from ..utils.firestore_signals import publish_signals, PAYMENTS_REVIEW_SIGNAL, PAYMENTS_CASHIER_SIGNAL
from ..auth.session_auth import (
    admin_cashier_employee_order_booker_required_from_session,
    admin_cashier_sales_required_from_session,
    admin_sales_required_from_session,
)
from .cash_deposit import (
    _read_slip_files, _delete_cloudinary, _get_slips, _user_names, _serialize as _serialize_deposit,
    _search_condition as _deposit_search_condition, _parse_search_date,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment-proofs", tags=["Payment Proofs"])
record_router = APIRouter(prefix="/payments-record", tags=["Payments Record"])

MAX_PROOF_IMAGES = 3
TYPE_DEPOSIT = "DEPOSIT"


# ---------- used by customer_invoice.py ----------

def new_payment_entry(amount, payment_method: str, date_iso: str, description: str) -> dict:
    """payments_history entry with an id, so a proof can point at it."""
    return {
        "id": str(uuid.uuid4()),
        "amount": float(amount),
        "payment_method": str(payment_method),
        "date": date_iso,
        "description": str(description),
    }


def proof_for_payment(invoice, entry: dict, user: User, source: str = SOURCE_CUSTOMIZED) -> Optional[PaymentProof]:
    """A MISSING proof for an online payment entry (None for cash / credit / other).
    invoice: CustomerInvoice (CUSTOMIZED) or walk-in Invoice (WALKIN). The caller adds
    it and commits."""
    if not is_online_method(entry.get("payment_method")):
        return None
    return PaymentProof(
        source=source,
        invoice_id=invoice.id,
        invoice_no=invoice.invoice_no,
        customer_name=invoice.customer_name,
        payment_id=entry["id"],
        amount=Decimal(str(entry["amount"])),
        payment_method=str(entry["payment_method"])[:50],
        payment_date=datetime.fromisoformat(entry["date"]).replace(tzinfo=None),
        status=PROOF_MISSING,
        recorded_by=user.id,
    )


async def delete_invoice_proofs(db: AsyncSession, invoice_id: UUID) -> Optional[List[Optional[str]]]:
    """Delete an invoice's proofs + image rows (caller commits). Returns the Cloudinary
    ids to remove after the commit, or None when the invoice had no proofs."""
    proofs = (await db.execute(select(PaymentProof).where(PaymentProof.invoice_id == invoice_id))).scalars().all()
    if not proofs:
        return None
    images = (await db.execute(
        select(PaymentProofImage).where(PaymentProofImage.proof_id.in_([p.id for p in proofs]))
    )).scalars().all()
    public_ids = [i.public_id for i in images]
    for image in images:
        await db.delete(image)
    await db.flush()
    for proof in proofs:
        await db.delete(proof)
    return public_ids


# ---------- helpers ----------

def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")


async def _get_proof_or_404(db: AsyncSession, proof_id: str, lock: bool = False) -> PaymentProof:
    """lock=True: row lock until commit, so two people approving / rejecting /
    uploading at the same moment cannot overwrite each other."""
    statement = select(PaymentProof).where(PaymentProof.id == _parse_uuid(proof_id))
    if lock:
        # populate_existing: a row already loaded in this session is re-read, not reused
        statement = statement.with_for_update().execution_options(populate_existing=True)
    proof = (await db.execute(statement)).scalar_one_or_none()
    if not proof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pay slip record not found")
    return proof


async def _get_images(db: AsyncSession, proof_ids: List[UUID]) -> dict:
    if not proof_ids:
        return {}
    result = await db.execute(
        select(PaymentProofImage).where(PaymentProofImage.proof_id.in_(proof_ids)).order_by(PaymentProofImage.id)
    )
    images: dict = {}
    for image in result.scalars().all():
        images.setdefault(image.proof_id, []).append(image)
    return images


def _serialize_proof(proof: PaymentProof, images: List[PaymentProofImage], names: dict) -> dict:
    return {
        "type": proof.source,
        "id": str(proof.id),
        "invoice_id": str(proof.invoice_id),
        "invoice_no": proof.invoice_no,
        "customer_name": proof.customer_name,
        "payment_id": proof.payment_id,
        "amount": float(proof.amount),
        "payment_method": proof.payment_method,
        "payment_date": proof.payment_date.isoformat() if proof.payment_date else None,
        "status": proof.status,
        "recorded_by_name": names.get(proof.recorded_by),
        "recorded_at": proof.recorded_at.isoformat() if proof.recorded_at else None,
        "uploaded_by_name": names.get(proof.uploaded_by) if proof.uploaded_by else None,
        "uploaded_at": proof.uploaded_at.isoformat() if proof.uploaded_at else None,
        "reviewed_by_name": names.get(proof.reviewed_by) if proof.reviewed_by else None,
        "reviewed_at": proof.reviewed_at.isoformat() if proof.reviewed_at else None,
        "reject_reason": proof.reject_reason,
        "branch": proof.branch,
        "images": [{"id": str(i.id), "file_url": i.file_url} for i in images],
    }


async def _proofs_response(db: AsyncSession, proofs: List[PaymentProof]) -> List[dict]:
    images = await _get_images(db, [p.id for p in proofs])
    user_ids = set()
    for p in proofs:
        user_ids |= {p.recorded_by, p.uploaded_by, p.reviewed_by}
    names = await _user_names(db, user_ids)
    return [_serialize_proof(p, images.get(p.id, []), names) for p in proofs]


def _proof_search_condition(search: str):
    """A date matches the payment date; otherwise invoice no, customer, method or amount."""
    search_date = _parse_search_date(search)
    if search_date:
        return cast(PaymentProof.payment_date, Date) == search_date
    like = f"%{search}%"
    conditions = [
        PaymentProof.invoice_no.ilike(like),
        PaymentProof.customer_name.ilike(like),
        PaymentProof.payment_method.ilike(like),
    ]
    try:
        amount = Decimal(search.replace(",", ""))
    except InvalidOperation:
        amount = None
    if amount is not None and amount.is_finite():
        conditions.append(PaymentProof.amount == amount)
    return or_(*conditions)


# ---------- payment proof endpoints (fixed paths before /{proof_id}) ----------

@router.get("/counts")
async def proof_counts(
    current_user: User = Depends(admin_cashier_employee_order_booker_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Proofs per status (sidebar badge / dashboard)."""
    result = await db.execute(select(PaymentProof.status, func.count(PaymentProof.id)).group_by(PaymentProof.status))
    counts = {row[0]: row[1] for row in result.all()}
    return {
        "pending": counts.get(PROOF_PENDING, 0),
        "missing": counts.get(PROOF_MISSING, 0),
        "rejected": counts.get(PROOF_REJECTED, 0),
    }


@router.get("/by-invoice/{invoice_id}")
async def proofs_of_invoice(
    invoice_id: str,
    current_user: User = Depends(admin_cashier_employee_order_booker_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """All proofs of one invoice (customer-payment page history)."""
    result = await db.execute(
        select(PaymentProof).where(PaymentProof.invoice_id == _parse_uuid(invoice_id)).order_by(PaymentProof.payment_date)
    )
    return {"data": await _proofs_response(db, result.scalars().all())}


@router.get("/{proof_id}")
async def get_proof(
    proof_id: str,
    current_user: User = Depends(admin_cashier_employee_order_booker_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    proof = await _get_proof_or_404(db, proof_id)
    return (await _proofs_response(db, [proof]))[0]


@router.put("/{proof_id}/images")
async def update_proof_images(
    proof_id: str,
    keep_image_ids: Optional[str] = Form(None, description="JSON list of existing image ids to keep (default: keep all)"),
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(admin_cashier_employee_order_booker_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Add / remove pay slips of a MISSING, PENDING or REJECTED proof. With images it
    becomes PENDING (a rejected one is resubmitted, like a cash deposit), with none
    MISSING. Anyone who records payments can upload."""
    proof = await _get_proof_or_404(db, proof_id)
    initial_status = proof.status
    if proof.status not in (PROOF_MISSING, PROOF_PENDING, PROOF_REJECTED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{proof.status.title()} payment cannot be changed")

    existing = (await _get_images(db, [proof.id])).get(proof.id, [])
    if keep_image_ids is None:
        keep_ids = {str(i.id) for i in existing}
    else:
        try:
            keep_ids = {str(i) for i in json.loads(keep_image_ids)}
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid keep_image_ids")
    removed = [i for i in existing if str(i.id) not in keep_ids]
    kept_count = len(existing) - len(removed)
    if kept_count + len(files) > MAX_PROOF_IMAGES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum {MAX_PROOF_IMAGES} pay slips per payment")

    contents = await _read_slip_files(files)
    uploaded = []
    try:
        for data in contents:
            uploaded.append(await CloudinaryService.upload_slip_image(
                data, public_id=f"proof_{uuid.uuid4().hex[:12]}", folder="payment-proofs"))
    except Exception as e:
        await _delete_cloudinary([u["public_id"] for u in uploaded])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    try:
        # Cloudinary upload takes seconds: re-read the status under a lock, so an
        # approve / reject done meanwhile is not turned back into PENDING
        proof = await _get_proof_or_404(db, proof_id, lock=True)
        if proof.status != initial_status and proof.status not in (PROOF_MISSING, PROOF_PENDING):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"This payment was {proof.status.lower()} meanwhile; pay slip not saved")
        for image in removed:
            await db.delete(image)
        for up in uploaded:
            db.add(PaymentProofImage(proof_id=proof.id, file_url=up["url"], public_id=up["public_id"]))
        if kept_count + len(uploaded) > 0:
            proof.status = PROOF_PENDING
            if uploaded:
                proof.uploaded_by = current_user.id
                proof.uploaded_at = datetime.now()
        else:
            proof.status = PROOF_MISSING
            proof.uploaded_by = None
            proof.uploaded_at = None
        # Resubmitted: back in the review queue, the old reject is cleared (like deposits)
        proof.reject_reason = None
        proof.reviewed_by = None
        proof.reviewed_at = None
        db.add(proof)
        await db.commit()
    except Exception:
        await db.rollback()
        await _delete_cloudinary([u["public_id"] for u in uploaded])
        raise

    await _delete_cloudinary([i.public_id for i in removed])
    await db.refresh(proof)
    logger.info(f"Payment proof {proof.invoice_no}/{proof.payment_id} images updated by {current_user.username}")
    await publish_signals(PAYMENTS_REVIEW_SIGNAL, PAYMENTS_CASHIER_SIGNAL)  # missing <-> pending
    return (await _proofs_response(db, [proof]))[0]


@router.post("/{proof_id}/approve")
async def approve_proof(
    proof_id: str,
    current_user: User = Depends(admin_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Money confirmed -> locked."""
    proof = await _get_proof_or_404(db, proof_id, lock=True)
    if proof.status == PROOF_MISSING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attach the pay slip before approving")
    if proof.status != PROOF_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{proof.status.title()} payment cannot be approved")
    proof.status = PROOF_APPROVED
    proof.reviewed_by = current_user.id
    proof.reviewed_at = datetime.now()
    db.add(proof)
    await db.commit()
    await db.refresh(proof)
    logger.info(f"Payment proof {proof.invoice_no}/{proof.payment_id} APPROVED by {current_user.username}")
    await publish_signals(PAYMENTS_REVIEW_SIGNAL)
    return (await _proofs_response(db, [proof]))[0]


@router.post("/{proof_id}/reject")
async def reject_proof(
    proof_id: str,
    body: PaymentProofReject,
    current_user: User = Depends(admin_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Money not received: reason required, the proof is locked as REJECTED. The
    invoice / bill is NOT changed (customized and walk-in, user decision 2026-10-09):
    staff follow up with the customer. A missing proof can be rejected too."""
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reject reason is required")
    proof = await _get_proof_or_404(db, proof_id, lock=True)
    if proof.status not in (PROOF_PENDING, PROOF_MISSING):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{proof.status.title()} payment cannot be rejected")

    proof.status = PROOF_REJECTED
    proof.reject_reason = reason[:500]
    proof.reviewed_by = current_user.id
    proof.reviewed_at = datetime.now()
    db.add(proof)
    await db.commit()
    await db.refresh(proof)
    logger.info(f"Payment proof {proof.invoice_no}/{proof.payment_id} ({proof.source}) REJECTED by {current_user.username}")
    await publish_signals(PAYMENTS_REVIEW_SIGNAL, PAYMENTS_CASHIER_SIGNAL)
    return (await _proofs_response(db, [proof]))[0]


# ---------- Payments Record: bank deposits + payment proofs in one list ----------

@record_router.get("/")
async def payments_record(
    page: int = 1,
    limit: int = 20,
    type_filter: Optional[str] = None,    # DEPOSIT / CUSTOMIZED / WALKIN, or PROOF = customized + walk-in
    status_filter: Optional[str] = None,  # PENDING / MISSING / APPROVED / REJECTED, or several: "REJECTED,MISSING"
    search: Optional[str] = None,
    from_date: Optional[str] = None,      # YYYY-MM-DD: only records from this day on (period filter)
    current_user: User = Depends(admin_cashier_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Newest first; every role sees all deposits and payment proofs of the branch."""
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    type_filter = (type_filter or "").upper() or None
    statuses = [x.strip() for x in (status_filter or "").upper().split(",") if x.strip()]
    search = (search or "").strip()[:100]
    since = None
    if from_date:
        try:
            since = datetime.combine(date.fromisoformat(from_date), datetime.min.time())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid from_date")

    parts = []
    if type_filter in (None, TYPE_DEPOSIT):
        deposits = select(
            literal(TYPE_DEPOSIT).label("kind"), CashDeposit.id.label("id"), CashDeposit.submitted_at.label("at"),
        )
        if since:
            deposits = deposits.where(CashDeposit.submitted_at >= since)
        if statuses:
            deposits = deposits.where(CashDeposit.status.in_(statuses))
        if search:
            deposits = deposits.where(_deposit_search_condition(search))
        parts.append(deposits)
    if type_filter != TYPE_DEPOSIT:
        proofs = select(
            PaymentProof.source.label("kind"), PaymentProof.id.label("id"), PaymentProof.recorded_at.label("at"),
        )
        if type_filter and type_filter != "PROOF":
            proofs = proofs.where(PaymentProof.source == type_filter)
        if since:
            proofs = proofs.where(PaymentProof.recorded_at >= since)
        if statuses:
            proofs = proofs.where(PaymentProof.status.in_(statuses))
        if search:
            proofs = proofs.where(_proof_search_condition(search))
        parts.append(proofs)

    combined = (union_all(*parts) if len(parts) > 1 else parts[0]).subquery()
    total = (await db.execute(select(func.count()).select_from(combined))).scalar_one()
    rows = (await db.execute(
        select(combined.c.kind, combined.c.id)
        .order_by(combined.c.at.desc(), combined.c.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )).all()

    deposit_ids = [r.id for r in rows if r.kind == TYPE_DEPOSIT]
    proof_ids = [r.id for r in rows if r.kind != TYPE_DEPOSIT]

    by_id: dict = {}
    if deposit_ids:
        deposit_rows = (await db.execute(select(CashDeposit).where(CashDeposit.id.in_(deposit_ids)))).scalars().all()
        slips = await _get_slips(db, deposit_ids)
        names = await _user_names(db, {d.submitted_by for d in deposit_rows} | {d.reviewed_by for d in deposit_rows})
        for d in deposit_rows:
            by_id[d.id] = {"type": TYPE_DEPOSIT, **_serialize_deposit(d, slips.get(d.id, []), names)}
    if proof_ids:
        proof_rows = (await db.execute(select(PaymentProof).where(PaymentProof.id.in_(proof_ids)))).scalars().all()
        for item in await _proofs_response(db, proof_rows):
            by_id[UUID(item["id"])] = item

    return {
        "data": [by_id[r.id] for r in rows if r.id in by_id],
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": (total + limit - 1) // limit if total else 1,
    }


@record_router.get("/pending-count")
async def payments_record_pending_count(
    current_user: User = Depends(admin_cashier_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Sidebar badge + dashboard. Sales/admin: deposits + proofs waiting for approval.
    Cashier: rejected deposits + rejected payments + payments without a pay slip
    (each stays until it is resubmitted / attached and becomes PENDING)."""
    is_cashier = current_user.role.name == "cashier"

    deposits_pending = select(func.count(CashDeposit.id)).where(CashDeposit.status == "PENDING")
    deposits_rejected = select(func.count(CashDeposit.id)).where(CashDeposit.status == "REJECTED")

    proof_counts_result = await db.execute(
        select(PaymentProof.status, func.count(PaymentProof.id))
        .where(PaymentProof.status.in_([PROOF_PENDING, PROOF_MISSING, PROOF_REJECTED]))
        .group_by(PaymentProof.status)
    )
    proof_counts = {row[0]: row[1] for row in proof_counts_result.all()}

    # Oldest few online payments waiting for a check (dashboard banner, sales/admin)
    proof_items = []
    if proof_counts.get(PROOF_PENDING) and not is_cashier:
        result = await db.execute(
            select(PaymentProof.invoice_no, PaymentProof.customer_name, PaymentProof.amount, PaymentProof.payment_method)
            .where(PaymentProof.status == PROOF_PENDING)
            .order_by(PaymentProof.uploaded_at)
            .limit(3)
        )
        proof_items = [
            {"invoice_no": r.invoice_no, "customer_name": r.customer_name, "amount": float(r.amount), "payment_method": r.payment_method}
            for r in result.all()
        ]

    return {
        "proof_items": proof_items,
        "deposits_pending": (await db.execute(deposits_pending)).scalar_one(),
        "deposits_rejected": (await db.execute(deposits_rejected)).scalar_one(),
        "proofs_pending": proof_counts.get(PROOF_PENDING, 0),
        "proofs_missing": proof_counts.get(PROOF_MISSING, 0),
        "proofs_rejected": proof_counts.get(PROOF_REJECTED, 0),
    }
