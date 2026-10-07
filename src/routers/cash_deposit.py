"""
Cash deposits: cash in hand taken to the bank, with bank slip images.

Flow: cashier/admin submit (PENDING) -> sales/admin approve (APPROVED, locked)
or reject with a reason (REJECTED) -> cashier edits and resubmits (PENDING).
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
from uuid import UUID
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
import json
import logging
import re
import uuid

from ..database.database import get_db
from ..config.branches import doc_prefix
from ..config.settings import settings
from ..models.user import User
from ..models.cash_deposit import (
    CashDeposit, CashDepositSlip,
    CashDepositReject, DEPOSIT_PENDING, DEPOSIT_APPROVED, DEPOSIT_REJECTED,
)
from ..services.cloudinary_service import CloudinaryService
from ..auth.session_auth import (
    cashier_required_from_session,
    admin_cashier_sales_required_from_session,
    admin_sales_required_from_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cash-deposits", tags=["Cash Deposits"])

ALLOWED_SLIP_TYPES = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
DEPOSIT_NO_LOCK = 765432  # pg advisory lock id for deposit number generation


# ---------- helpers ----------

def _parse_date(value: Optional[str], field: str) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field} date")


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid deposit ID format")


def _parse_slip_infos(raw: Optional[str], field: str) -> List[dict]:
    """JSON list of {bank_name, slip_no, amount} (optionally with id) from a form field."""
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}")
    if not isinstance(items, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}")

    parsed = []
    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}")
        bank_name = str(item.get("bank_name") or "").strip()
        if not bank_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slip {i}: bank name is required")
        try:
            amount = Decimal(str(item.get("amount"))).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slip {i}: invalid amount")
        if amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slip {i}: amount must be greater than 0")
        slip_no = str(item.get("slip_no") or "").strip() or None
        parsed.append({
            "id": item.get("id"),
            "bank_name": bank_name[:100],
            "slip_no": slip_no[:100] if slip_no else None,
            "amount": amount,
        })
    return parsed


async def _read_slip_files(files: List[UploadFile]) -> List[bytes]:
    """Validate (images only, size limit) and read uploaded slip files."""
    contents = []
    for i, file in enumerate(files, start=1):
        if file.content_type not in ALLOWED_SLIP_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Slip {i}: only JPG, PNG or WebP images are allowed",
            )
        data = await file.read()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slip {i}: file is empty")
        if len(data) > settings.max_upload_size:
            max_mb = settings.max_upload_size // (1024 * 1024)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slip {i}: file must be less than {max_mb}MB")
        contents.append(data)
    return contents


async def _upload_slips(contents: List[bytes]) -> List[dict]:
    """Upload all slips; on failure remove the ones already uploaded."""
    uploaded = []
    try:
        for data in contents:
            uploaded.append(await CloudinaryService.upload_slip_image(data, public_id=f"slip_{uuid.uuid4().hex[:12]}"))
    except Exception as e:
        await _delete_cloudinary([u["public_id"] for u in uploaded])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return uploaded


async def _delete_cloudinary(public_ids: List[Optional[str]]):
    for public_id in public_ids:
        if public_id:
            await CloudinaryService.delete_image(public_id)


async def _generate_deposit_no(db: AsyncSession) -> str:
    # Transaction-level lock: held until commit, so two submits never get the same number
    await db.execute(select(func.pg_advisory_xact_lock(DEPOSIT_NO_LOCK)))
    prefix = doc_prefix("DEP")
    result = await db.execute(
        select(CashDeposit.deposit_no)
        .where(CashDeposit.deposit_no.like(prefix + "%"))
        # Numeric max: longer number first, so e.g. DEP-10000 beats DEP-9999
        .order_by(func.length(CashDeposit.deposit_no).desc(), CashDeposit.deposit_no.desc())
        .limit(1)
    )
    max_no = result.scalar_one_or_none()
    seq = max_no.split("-")[-1] if max_no else ""
    next_seq = int(seq) + 1 if seq.isdigit() else 1
    return f"{prefix}{next_seq:04d}"


async def _get_deposit_or_404(db: AsyncSession, deposit_id: str, current_user: User) -> CashDeposit:
    deposit = await db.get(CashDeposit, _parse_uuid(deposit_id))
    # Cashier only sees their own deposits
    if not deposit or (current_user.role.name == "cashier" and deposit.submitted_by != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deposit not found")
    return deposit


async def _get_slips(db: AsyncSession, deposit_ids: List[UUID]) -> dict:
    if not deposit_ids:
        return {}
    result = await db.execute(
        select(CashDepositSlip).where(CashDepositSlip.deposit_id.in_(deposit_ids)).order_by(CashDepositSlip.id)
    )
    slips_by_deposit: dict = {}
    for slip in result.scalars().all():
        slips_by_deposit.setdefault(slip.deposit_id, []).append(slip)
    return slips_by_deposit


async def _user_names(db: AsyncSession, user_ids: set) -> dict:
    ids = [u for u in user_ids if u]
    if not ids:
        return {}
    result = await db.execute(select(User.id, User.full_name, User.username).where(User.id.in_(ids)))
    return {row.id: (row.full_name or row.username) for row in result.all()}


def _serialize(deposit: CashDeposit, slips: List[CashDepositSlip], names: dict) -> dict:
    return {
        "id": str(deposit.id),
        "deposit_no": deposit.deposit_no,
        "cash_from": deposit.cash_from.isoformat(),
        "cash_to": deposit.cash_to.isoformat(),
        "deposit_date": deposit.deposit_date.isoformat(),
        "total_amount": float(deposit.total_amount),
        "notes": deposit.notes,
        "status": deposit.status,
        "submitted_by": str(deposit.submitted_by),
        "submitted_by_name": names.get(deposit.submitted_by),
        "submitted_at": deposit.submitted_at.isoformat() if deposit.submitted_at else None,
        "reviewed_by": str(deposit.reviewed_by) if deposit.reviewed_by else None,
        "reviewed_by_name": names.get(deposit.reviewed_by) if deposit.reviewed_by else None,
        "reviewed_at": deposit.reviewed_at.isoformat() if deposit.reviewed_at else None,
        "reject_reason": deposit.reject_reason,
        "branch": deposit.branch,
        "slip_count": len(slips),
        "slips": [
            {
                "id": str(s.id),
                "file_url": s.file_url,
                "bank_name": s.bank_name,
                "slip_no": s.slip_no,
                "amount": float(s.amount),
            }
            for s in slips
        ],
    }


async def _deposit_response(db: AsyncSession, deposit: CashDeposit) -> dict:
    slips = (await _get_slips(db, [deposit.id])).get(deposit.id, [])
    names = await _user_names(db, {deposit.submitted_by, deposit.reviewed_by})
    return _serialize(deposit, slips, names)


def _parse_search_date(text: str) -> Optional[date]:
    """dd/mm or dd/mm/yyyy (also -); no year -> current year. No "." so 12.5 stays an amount."""
    match = re.fullmatch(r"(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2}|\d{4}))?", text)
    if not match:
        return None
    day, month, year = match.groups()
    year = int(year) if year else date.today().year
    if year < 100:
        year += 2000
    try:
        return date(year, int(month), int(day))
    except ValueError:
        return None


def _search_condition(search: str):
    """Smart search: a date matches Cash Of range or Deposit Date; otherwise
    deposit no, bank name, submitted by name, or amount (total / slip)."""
    search_date = _parse_search_date(search)
    if search_date:
        return or_(
            (CashDeposit.cash_from <= search_date) & (CashDeposit.cash_to >= search_date),
            CashDeposit.deposit_date == search_date,
        )

    like = f"%{search}%"
    conditions = [
        CashDeposit.deposit_no.ilike(like),
        select(CashDepositSlip.id)
        .where(CashDepositSlip.deposit_id == CashDeposit.id, CashDepositSlip.bank_name.ilike(like))
        .exists(),
        select(User.id)
        .where(User.id == CashDeposit.submitted_by, or_(User.full_name.ilike(like), User.username.ilike(like)))
        .exists(),
    ]
    try:
        amount = Decimal(search.replace(",", ""))
    except InvalidOperation:
        amount = None
    if amount is not None and amount.is_finite():
        conditions.append(CashDeposit.total_amount == amount)
        conditions.append(
            select(CashDepositSlip.id)
            .where(CashDepositSlip.deposit_id == CashDeposit.id, CashDepositSlip.amount == amount)
            .exists()
        )
    return or_(*conditions)


def _apply_filters(statement, current_user: User, status_filter: Optional[str], search: Optional[str]):
    if current_user.role.name == "cashier":
        statement = statement.where(CashDeposit.submitted_by == current_user.id)
    if status_filter:
        statement = statement.where(CashDeposit.status == status_filter.upper())
    search = (search or "").strip()
    if search:
        statement = statement.where(_search_condition(search[:100]))
    return statement


def _validate_dates(cash_from: date, cash_to: date):
    if cash_from > cash_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cash From date must be before Cash To date")


# ---------- endpoints (fixed paths before /{deposit_id}) ----------

@router.get("/")
async def list_deposits(
    page: int = 1,
    limit: int = 20,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(admin_cashier_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """List deposits (newest first). Cashier: only their own."""
    page = max(page, 1)
    limit = min(max(limit, 1), 100)

    count_statement = _apply_filters(select(func.count(CashDeposit.id)), current_user, status_filter, search)
    total = (await db.execute(count_statement)).scalar_one()

    statement = _apply_filters(select(CashDeposit), current_user, status_filter, search)
    statement = statement.order_by(CashDeposit.submitted_at.desc()).offset((page - 1) * limit).limit(limit)
    deposits = (await db.execute(statement)).scalars().all()

    slips_by_deposit = await _get_slips(db, [d.id for d in deposits])
    names = await _user_names(db, {d.submitted_by for d in deposits} | {d.reviewed_by for d in deposits})

    return {
        "data": [_serialize(d, slips_by_deposit.get(d.id, []), names) for d in deposits],
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": (total + limit - 1) // limit if total else 1,
    }


@router.get("/pending-count")
async def pending_count(
    current_user: User = Depends(admin_cashier_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Pending deposits (cashier: own pending; sales/admin: all) + cashier's rejected count.
    Sales/admin also get the oldest few pending (deposit no + Cash Of) for the dashboard."""
    statement = select(func.count(CashDeposit.id)).where(CashDeposit.status == DEPOSIT_PENDING)
    rejected_statement = select(func.count(CashDeposit.id)).where(CashDeposit.status == DEPOSIT_REJECTED)
    is_cashier = current_user.role.name == "cashier"
    if is_cashier:
        statement = statement.where(CashDeposit.submitted_by == current_user.id)
        rejected_statement = rejected_statement.where(CashDeposit.submitted_by == current_user.id)
    pending = (await db.execute(statement)).scalar_one()

    items = []
    if pending and not is_cashier:
        result = await db.execute(
            select(CashDeposit.deposit_no, CashDeposit.cash_from, CashDeposit.cash_to)
            .where(CashDeposit.status == DEPOSIT_PENDING)
            .order_by(CashDeposit.submitted_at)
            .limit(3)
        )
        items = [
            {"deposit_no": row.deposit_no, "cash_from": row.cash_from.isoformat(), "cash_to": row.cash_to.isoformat()}
            for row in result.all()
        ]

    return {
        "pending": pending,
        "rejected": (await db.execute(rejected_statement)).scalar_one(),
        "items": items,
    }


@router.get("/{deposit_id}")
async def get_deposit(
    deposit_id: str,
    current_user: User = Depends(admin_cashier_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    deposit = await _get_deposit_or_404(db, deposit_id, current_user)
    return await _deposit_response(db, deposit)


@router.post("/")
async def create_deposit(
    cash_from: str = Form(...),
    cash_to: str = Form(...),
    deposit_date: str = Form(...),
    notes: Optional[str] = Form(None),
    slips: str = Form(..., description='JSON list: [{"bank_name", "slip_no", "amount"}], same order as files'),
    files: List[UploadFile] = File(..., description="Slip images (JPG/PNG/WebP)"),
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Submit a deposit with one or more slips -> PENDING. Admin + cashier."""
    cash_from_d = _parse_date(cash_from, "Cash From")
    cash_to_d = _parse_date(cash_to, "Cash To")
    deposit_date_d = _parse_date(deposit_date, "deposit")
    _validate_dates(cash_from_d, cash_to_d)

    slip_infos = _parse_slip_infos(slips, "slips")
    if not slip_infos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one slip is required")
    if len(files) != len(slip_infos):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Every slip needs one image")

    contents = await _read_slip_files(files)
    uploaded = await _upload_slips(contents)

    try:
        deposit = CashDeposit(
            deposit_no=await _generate_deposit_no(db),
            cash_from=cash_from_d,
            cash_to=cash_to_d,
            deposit_date=deposit_date_d,
            total_amount=sum((s["amount"] for s in slip_infos), Decimal("0")),
            notes=(notes or "").strip()[:500] or None,
            status=DEPOSIT_PENDING,
            submitted_by=current_user.id,
        )
        db.add(deposit)
        await db.flush()
        for info, up in zip(slip_infos, uploaded):
            db.add(CashDepositSlip(
                deposit_id=deposit.id,
                file_url=up["url"],
                public_id=up["public_id"],
                bank_name=info["bank_name"],
                slip_no=info["slip_no"],
                amount=info["amount"],
            ))
        await db.commit()
    except Exception:
        await db.rollback()
        await _delete_cloudinary([u["public_id"] for u in uploaded])
        raise

    await db.refresh(deposit)
    logger.info(f"Cash deposit {deposit.deposit_no} submitted by {current_user.username}")
    return await _deposit_response(db, deposit)


@router.put("/{deposit_id}")
async def update_deposit(
    deposit_id: str,
    cash_from: Optional[str] = Form(None),
    cash_to: Optional[str] = Form(None),
    deposit_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    slip_updates: Optional[str] = Form(None, description='JSON list of existing slips to keep: [{"id", "bank_name", "slip_no", "amount"}]'),
    new_slips: Optional[str] = Form(None, description='JSON list for new files: [{"bank_name", "slip_no", "amount"}]'),
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Edit a PENDING / REJECTED deposit. Existing slips not in slip_updates are removed.
    Saving always puts it back to PENDING (resubmit) and clears the reject reason."""
    deposit = await _get_deposit_or_404(db, deposit_id, current_user)
    if deposit.status == DEPOSIT_APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approved deposit cannot be edited")

    new_from = _parse_date(cash_from, "Cash From") or deposit.cash_from
    new_to = _parse_date(cash_to, "Cash To") or deposit.cash_to
    _validate_dates(new_from, new_to)
    new_deposit_date = _parse_date(deposit_date, "deposit") or deposit.deposit_date

    existing = (await _get_slips(db, [deposit.id])).get(deposit.id, [])
    existing_by_id = {str(s.id): s for s in existing}
    keep_infos = _parse_slip_infos(slip_updates, "slip_updates") if slip_updates is not None else [
        {"id": str(s.id), "bank_name": s.bank_name, "slip_no": s.slip_no, "amount": s.amount} for s in existing
    ]
    for info in keep_infos:
        if str(info.get("id")) not in existing_by_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown slip in slip_updates")

    new_infos = _parse_slip_infos(new_slips, "new_slips")
    if len(files) != len(new_infos):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Every new slip needs one image")
    if not keep_infos and not new_infos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one slip is required")

    contents = await _read_slip_files(files)
    uploaded = await _upload_slips(contents)

    keep_ids = {str(info["id"]) for info in keep_infos}
    removed = [s for s in existing if str(s.id) not in keep_ids]
    try:
        for info in keep_infos:
            slip = existing_by_id[str(info["id"])]
            slip.bank_name = info["bank_name"]
            slip.slip_no = info["slip_no"]
            slip.amount = info["amount"]
            db.add(slip)
        for slip in removed:
            await db.delete(slip)
        for info, up in zip(new_infos, uploaded):
            db.add(CashDepositSlip(
                deposit_id=deposit.id,
                file_url=up["url"],
                public_id=up["public_id"],
                bank_name=info["bank_name"],
                slip_no=info["slip_no"],
                amount=info["amount"],
            ))

        deposit.cash_from = new_from
        deposit.cash_to = new_to
        deposit.deposit_date = new_deposit_date
        if notes is not None:
            deposit.notes = notes.strip()[:500] or None
        deposit.total_amount = sum((i["amount"] for i in keep_infos + new_infos), Decimal("0"))
        deposit.status = DEPOSIT_PENDING
        deposit.reject_reason = None
        deposit.reviewed_by = None
        deposit.reviewed_at = None
        deposit.submitted_at = datetime.now()
        db.add(deposit)
        await db.commit()
    except Exception:
        await db.rollback()
        await _delete_cloudinary([u["public_id"] for u in uploaded])
        raise

    # Only after the DB change is saved
    await _delete_cloudinary([s.public_id for s in removed])
    await db.refresh(deposit)
    logger.info(f"Cash deposit {deposit.deposit_no} edited/resubmitted by {current_user.username}")
    return await _deposit_response(db, deposit)


async def _review(db: AsyncSession, deposit_id: str, current_user: User, new_status: str,
                  reason: Optional[str] = None) -> dict:
    deposit = await _get_deposit_or_404(db, deposit_id, current_user)
    if deposit.status == DEPOSIT_APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deposit is already approved")
    if deposit.status != DEPOSIT_PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending deposits can be reviewed")

    deposit.status = new_status
    deposit.reject_reason = reason
    deposit.reviewed_by = current_user.id
    deposit.reviewed_at = datetime.now()
    db.add(deposit)
    await db.commit()
    await db.refresh(deposit)
    logger.info(f"Cash deposit {deposit.deposit_no} {new_status} by {current_user.username}")
    return await _deposit_response(db, deposit)


@router.post("/{deposit_id}/approve")
async def approve_deposit(
    deposit_id: str,
    current_user: User = Depends(admin_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Approve -> locked (no more edit / review)."""
    return await _review(db, deposit_id, current_user, DEPOSIT_APPROVED)


@router.post("/{deposit_id}/reject")
async def reject_deposit(
    deposit_id: str,
    body: CashDepositReject,
    current_user: User = Depends(admin_sales_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """Reject with a reason (required); cashier can then edit and resubmit."""
    reason = (body.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reject reason is required")
    return await _review(db, deposit_id, current_user, DEPOSIT_REJECTED, reason[:500])
