"""
Shop batches (LH / KA), BATCH_COSTING_PLAN.md sec 12. Same dhaancha as the warehouse lots:
a batch (location "shop") with vendors inside (BatchVendor.vendor_id = a shop vendor), but no
bill - a line's cost / selling price are typed at its first Stock In and then stay.

Every branch has the same shop batches: the number is one count over all branches, and a
batch / vendor / line made in one branch is copied to the others (same id / barcode / price,
stock 0), like a product. Copies are made after this branch's save; a branch that could not
be reached gets a warning (a later line copy also makes its missing batch / vendor there).
"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.branches import BRANCHES, DEFAULT_BRANCH, configured_branches, current_branch
from ..database.database import session_factories
from ..models.batch import Batch, BatchVendor, ProductBatch, BATCH_OPEN, LOCATION_SHOP
from ..models.product import Product
from ..models.user import User
from ..models.vendor import Vendor
from ..models.warehouse_vendor import vendor_code_for
from ..utils.batch_barcode import make_batch_barcode
from .batch_service import barcode_taken

logger = logging.getLogger(__name__)

SHOP_BATCH_NO_LOCK = 765435  # pg advisory lock (Light House DB) for shop batch numbers
SHOP_VENDOR_CODE_LOCK = 765436  # pg advisory lock (Light House DB) for shop vendor codes


def other_branches() -> List[str]:
    here = current_branch.get()
    return [b.code for b in configured_branches() if b.code != here and b.code in session_factories]


def all_branches() -> List[str]:
    return [b.code for b in configured_branches() if b.code in session_factories]


def shop_batch_label(batch: Batch) -> str:
    return f"Shop Batch {batch.batch_no:03d}"


def _same_name(name: str):
    return func.lower(func.trim(Vendor.name)) == (name or "").strip().lower()


def _code_no(code: str) -> int:
    """Inverse of vendor_code_for: 001 -> 1, 9000 -> 900."""
    return int(code) if len(code) == 3 else 900 * (len(code) - 3) + int(code[-3:])


# ---------- numbers / codes (one count over all branches) ----------

async def next_shop_batch_no(lock_db: AsyncSession, db: Optional[AsyncSession] = None) -> int:
    """Next shop batch number over every branch (and `db`, this request's session). lock_db is
    a Light House session: the lock is held until it commits, so two shops never get one number."""
    await lock_db.execute(select(func.pg_advisory_xact_lock(SHOP_BATCH_NO_LOCK)))
    highest = 0
    if db is not None:
        highest = (await db.execute(
            select(func.max(Batch.batch_no)).where(Batch.location == LOCATION_SHOP)
        )).scalar_one_or_none() or 0
    for code in all_branches():
        async with session_factories[code]() as db:
            n = (await db.execute(
                select(func.max(Batch.batch_no)).where(Batch.location == LOCATION_SHOP)
            )).scalar_one_or_none()
            highest = max(highest, n or 0)
    return highest + 1


async def peek_shop_batch_no(db: AsyncSession) -> int:
    """The number the next shop batch will get, for the New Batch form: no lock, every
    branch asked at once (fast). create uses next_shop_batch_no, which locks."""
    async def highest_in(code: str) -> int:
        async with session_factories[code]() as other:
            return (await other.execute(
                select(func.max(Batch.batch_no)).where(Batch.location == LOCATION_SHOP)
            )).scalar_one_or_none() or 0
    here = current_branch.get()
    local = (await db.execute(
        select(func.max(Batch.batch_no)).where(Batch.location == LOCATION_SHOP)
    )).scalar_one_or_none() or 0
    others = await asyncio.gather(*[highest_in(c) for c in all_branches() if c != here], return_exceptions=True)
    return max([local] + [n for n in others if isinstance(n, int)]) + 1


async def ensure_vendor_code(db: AsyncSession, vendor: Vendor) -> str:
    """The shop vendor's code for batch barcodes: the same name has the same code in every
    branch; a new name gets the next code over all branches. The caller commits."""
    if vendor.vendor_code:
        return vendor.vendor_code
    async with session_factories[DEFAULT_BRANCH]() as lock_db:
        await lock_db.execute(select(func.pg_advisory_xact_lock(SHOP_VENDOR_CODE_LOCK)))
        code, highest = None, 0
        for branch in all_branches():
            async with session_factories[branch]() as other:
                found = (await other.execute(
                    select(Vendor.vendor_code).where(_same_name(vendor.name), Vendor.vendor_code.isnot(None)).limit(1)
                )).scalar_one_or_none()
                code = code or found
                for (c,) in (await other.execute(select(Vendor.vendor_code).where(Vendor.vendor_code.isnot(None)))).all():
                    highest = max(highest, _code_no(c))
        vendor.vendor_code = code or vendor_code_for(highest + 1)
        db.add(vendor)
        await db.flush()
        await lock_db.commit()
    return vendor.vendor_code


# ---------- Stock In ----------

async def open_shop_batch_vendor(db: AsyncSession, batch_id: str, vendor_id: UUID) -> Tuple[Batch, BatchVendor]:
    """The shop batch a Stock In goes into: OPEN, with the chosen vendor in it."""
    try:
        batch = await db.get(Batch, UUID(str(batch_id)))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch ID format")
    if not batch or batch.location != LOCATION_SHOP:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop batch not found")
    if batch.status != BATCH_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{shop_batch_label(batch)} is closed - choose an open batch")
    batch_vendor = (await db.execute(
        select(BatchVendor).where(BatchVendor.batch_id == batch.id, BatchVendor.vendor_id == vendor_id)
    )).scalar_one_or_none()
    if not batch_vendor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Add this vendor to {shop_batch_label(batch)} first")
    return batch, batch_vendor


async def saved_shop_line(db: AsyncSession, product_id: UUID, batch_vendor_id: UUID) -> Optional[ProductBatch]:
    return (await db.execute(
        select(ProductBatch).where(ProductBatch.product_id == product_id, ProductBatch.batch_vendor_id == batch_vendor_id)
    )).scalar_one_or_none()


async def stock_into_shop_batch(db: AsyncSession, product: Product, batch: Batch, batch_vendor: BatchVendor,
                                vendor: Vendor, qty: int, cost: Decimal, selling: Decimal) -> Tuple[ProductBatch, bool]:
    """Add qty to the product's line of this vendor in the shop batch. The first Stock In
    makes the line (batch barcode) with the cost / price typed; later ones only add stock -
    the saved cost / price stay. The caller updates product.stock_level, writes the stock
    entry (at the line's cost) and commits. Returns (line, True if made now)."""
    if not product.barcode:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{product.name} has no barcode")
    line = await saved_shop_line(db, product.id, batch_vendor.id)
    is_new = line is None
    if is_new:
        if cost <= 0 or selling <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"{product.name}: cost and selling price must be more than 0")
        code = await ensure_vendor_code(db, vendor)
        barcode = make_batch_barcode(product.barcode, code, batch.batch_no)
        taken = await barcode_taken(db, barcode)
        if taken:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Barcode {barcode} already belongs to {taken} - not saved")
        now = datetime.now()
        line = ProductBatch(product_id=product.id, batch_id=batch.id, batch_vendor_id=batch_vendor.id,
                            barcode=barcode, cost=cost, landed_cost=cost, selling_price=selling,
                            shop_cost=cost, shop_price=selling, warehouse_stock=0, stock_level=0,
                            created_at=now, updated_at=now)
    line.stock_level = (line.stock_level or 0) + qty
    line.updated_at = datetime.now()
    db.add(line)
    await db.flush()
    return line, is_new


def line_cost(line: ProductBatch) -> Decimal:
    return line.shop_cost if line.shop_cost is not None else line.cost


def line_price(line: ProductBatch) -> Decimal:
    return line.shop_price if line.shop_price is not None else line.selling_price


# ---------- copies in the other branches ----------

async def _user_there(db: AsyncSession, user_id: UUID) -> UUID:
    """created_by in another branch: the same user, else any user there (users are per DB)."""
    if await db.get(User, user_id):
        return user_id
    return (await db.execute(select(User.id).limit(1))).scalar_one()


async def _vendor_there(db: AsyncSession, name: str, code: Optional[str], branch_name: str) -> Vendor:
    """The shop vendor of this name in another branch, made (balance 0) if missing."""
    vendor = (await db.execute(select(Vendor).where(_same_name(name)).limit(1))).scalar_one_or_none()
    if vendor is None:
        vendor = Vendor(name=name.strip(), contacts="{}", branch=branch_name, balance=Decimal("0"),
                        payments_history="[]", vendor_code=code)
        db.add(vendor)
        await db.flush()
    elif not vendor.vendor_code and code:
        vendor.vendor_code = code
        db.add(vendor)
    return vendor


async def _copy_batch(db: AsyncSession, batch: Batch) -> Batch:
    copy = await db.get(Batch, batch.id)
    if copy is None:
        copy = Batch(id=batch.id, location=LOCATION_SHOP, batch_no=batch.batch_no, batch_date=batch.batch_date,
                     status=batch.status, note=batch.note, created_by=await _user_there(db, batch.created_by),
                     created_at=batch.created_at, updated_at=batch.updated_at)
        db.add(copy)
        await db.flush()
    return copy


async def _copy_batch_vendor(db: AsyncSession, batch: Batch, batch_vendor: BatchVendor, vendor: Vendor,
                             branch_name: str) -> BatchVendor:
    await _copy_batch(db, batch)
    copy = await db.get(BatchVendor, batch_vendor.id)
    if copy is None:
        there = await _vendor_there(db, vendor.name, vendor.vendor_code, branch_name)
        copy = BatchVendor(id=batch_vendor.id, batch_id=batch.id, vendor_id=there.id,
                           bill_date=batch_vendor.bill_date, invoice_total=Decimal("0"),
                           created_by=await _user_there(db, batch_vendor.created_by),
                           created_at=batch_vendor.created_at, updated_at=batch_vendor.updated_at)
        db.add(copy)
        await db.flush()
    return copy


async def _each_other_branch(what: str, work) -> List[str]:
    """Run work(db, branch) in every other branch, each committed on its own; warnings for
    the ones that failed."""
    warnings: List[str] = []
    for code in other_branches():
        branch = BRANCHES[code]
        try:
            async with session_factories[code]() as db:
                await work(db, branch)
                await db.commit()
        except HTTPException as e:
            warnings.append(f"{what} not done in {branch.name}: {e.detail}"[:300])
        except Exception as e:
            logger.exception("%s in %s failed", what, code)
            warnings.append(f"{what} not done in {branch.name}: {str(e) or type(e).__name__}"[:300])
    return warnings


async def mirror_batch(batch: Batch) -> List[str]:
    """New batch / date / note / status: the same in the other branches."""
    async def work(db, branch):
        copy = await _copy_batch(db, batch)
        copy.batch_date, copy.note, copy.status = batch.batch_date, batch.note, batch.status
        copy.closed_at = batch.closed_at
        copy.updated_at = batch.updated_at
        db.add(copy)
    return await _each_other_branch(f"{shop_batch_label(batch)}", work)


async def mirror_batch_delete(batch: Batch) -> List[str]:
    """Delete the copies too - not where stock already went into it."""
    async def work(db, branch):
        copy = await db.get(Batch, batch.id)
        if copy is None:
            return
        if (await db.execute(select(ProductBatch.id).where(ProductBatch.batch_id == copy.id).limit(1))).first():
            raise HTTPException(status_code=400, detail="stock was added there")
        for bv in (await db.execute(select(BatchVendor).where(BatchVendor.batch_id == copy.id))).scalars().all():
            await db.delete(bv)
        await db.flush()
        await db.delete(copy)
    return await _each_other_branch(f"Deleting {shop_batch_label(batch)}", work)


async def mirror_batch_vendor(batch: Batch, batch_vendor: BatchVendor, vendor: Vendor) -> List[str]:
    async def work(db, branch):
        await _copy_batch_vendor(db, batch, batch_vendor, vendor, branch.name)
    return await _each_other_branch(f"{vendor.name.strip()} in {shop_batch_label(batch)}", work)


async def mirror_batch_vendor_delete(batch: Batch, batch_vendor_id: UUID, vendor_name: str) -> List[str]:
    async def work(db, branch):
        copy = await db.get(BatchVendor, batch_vendor_id)
        if copy is None:
            return
        if (await db.execute(select(ProductBatch.id).where(ProductBatch.batch_vendor_id == copy.id).limit(1))).first():
            raise HTTPException(status_code=400, detail="stock was added there")
        await db.delete(copy)
    return await _each_other_branch(f"Removing {vendor_name} from {shop_batch_label(batch)}", work)


async def mirror_shop_line(line: ProductBatch, product_barcode: str, batch: Batch, batch_vendor: BatchVendor,
                           vendor: Vendor) -> List[str]:
    """A new shop batch line: in the other branches with the same barcode / cost / price,
    stock 0, under the copied batch + vendor (so a Stock In there finds it saved)."""
    async def work(db, branch):
        if (await db.execute(select(ProductBatch.id).where(ProductBatch.barcode == line.barcode).limit(1))).first():
            return
        product_id = (await db.execute(select(Product.id).where(Product.barcode == product_barcode))).scalar_one_or_none()
        if product_id is None:
            raise HTTPException(status_code=400, detail="product not there")
        copy_vendor = await _copy_batch_vendor(db, batch, batch_vendor, vendor, branch.name)
        now = datetime.now()
        db.add(ProductBatch(product_id=product_id, batch_id=batch.id, batch_vendor_id=copy_vendor.id,
                            barcode=line.barcode, cost=line.cost, landed_cost=line.landed_cost,
                            selling_price=line.selling_price, shop_cost=line.shop_cost, shop_price=line.shop_price,
                            warehouse_stock=0, stock_level=0, created_at=now, updated_at=now))
    return await _each_other_branch(f"Batch line {line.barcode}", work)
