"""
Shop -> shop stock transfer between branches (STOCK_TRANSFER_PLAN.md).

The logged-in branch sends shop stock (`stock_level`) to another branch, which
has its own database. Products are matched by barcode; a product missing in the
receiving branch is never auto-created - the item is blocked with a warning.

Two databases cannot commit atomically: the sending DB commits first, then the
receiving DB. If the receiving commit fails, the sending side is reversed in the
same request, so a transfer is either applied in both branches or in neither.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.branches import BRANCHES, current_branch
from ..database.database import session_factories
from ..models.product import Product
from ..models.stock_entry import StockEntry, StockEntryType
from ..models.user import User
from ..models.vendor import Vendor

logger = logging.getLogger(__name__)

# Serializes transfers in both DBs (transaction-scoped lock)
SHOP_TRANSFER_LOCK_ID = 123463

# Same item/qty sent again within this window is treated as a double-click
DUPLICATE_TRANSFER_WINDOW_SECONDS = 30

TRANSFER_IN = "Transfer In"
TRANSFER_OUT = "Transfer Out"
TRANSFER_LOCATIONS = (TRANSFER_IN, TRANSFER_OUT)


class ShopTransferError(Exception):
    """Transfer cannot be applied; message is shown to the user."""


def transfer_ref(direction: str, branch_code: str, now: datetime) -> str:
    """direction: TO (sending side) / FROM (receiving side)"""
    return f"TRANSFER_{direction}_{branch_code}_{now.strftime('%Y%m%d_%H%M%S')}"


def transfer_label(entry: StockEntry) -> Optional[str]:
    """Report text for a transfer entry, e.g. "Transfer Out → European Sports Karim Abad".
    None for entries that are not transfers."""
    if entry.location not in TRANSFER_LOCATIONS:
        return None
    parts = (entry.ref or "").split("_")
    other = BRANCHES.get(parts[2]).name if len(parts) > 2 and parts[2] in BRANCHES else "?"
    arrow = "→" if entry.location == TRANSFER_OUT else "←"
    return f"{entry.location} {arrow} {other}"


def other_branches(from_code: str) -> List[str]:
    return [code for code in BRANCHES if code != from_code]


def resolve_target(from_code: str, to_code: Optional[str]) -> str:
    if not to_code:
        others = other_branches(from_code)
        if len(others) != 1:
            raise ShopTransferError("Select the branch to send stock to")
        to_code = others[0]
    if to_code == from_code or to_code not in BRANCHES:
        raise ShopTransferError("Invalid branch to send stock to")
    if to_code not in session_factories:
        raise ShopTransferError(f"{BRANCHES[to_code].name} database is not configured")
    return to_code


def _merge_items(items: List[dict]) -> Dict[uuid.UUID, int]:
    """product_id -> total qty (the same product added twice counts once)"""
    merged: Dict[uuid.UUID, int] = {}
    for item in items:
        try:
            product_id = uuid.UUID(str(item.get("product_id")))
            quantity = int(item.get("quantity") or 0)
        except (ValueError, TypeError):
            raise ShopTransferError("Invalid product or quantity")
        merged[product_id] = merged.get(product_id, 0) + quantity
    return merged


def _same_name(a: Optional[str], b: Optional[str]) -> bool:
    return " ".join((a or "").lower().split()) == " ".join((b or "").lower().split())


async def check_items(
    src_db: AsyncSession, dst_db: AsyncSession, to_code: str,
    items: List[dict], lock: bool = False,
) -> List[dict]:
    """Status of every item for sending to `to_code`:
    ok / warning (can send) / error (blocked). Writes nothing.
    lock=True locks the sending products (FOR UPDATE) for the save."""
    to_name = BRANCHES[to_code].name
    merged = _merge_items(items)

    statement = select(Product).where(Product.id.in_(list(merged)))
    if lock:
        statement = statement.with_for_update()
    src_result = await src_db.execute(statement.execution_options(populate_existing=True))
    src_products = {p.id: p for p in src_result.scalars().all()}

    barcodes = [p.barcode for p in src_products.values() if p.barcode]
    skus = [p.sku for p in src_products.values() if p.sku]
    dst_by_barcode: Dict[str, List[Product]] = {}
    dst_by_sku: Dict[str, Product] = {}
    if barcodes:
        dst_result = await dst_db.execute(select(Product).where(Product.barcode.in_(barcodes)))
        for p in dst_result.scalars().all():
            dst_by_barcode.setdefault(p.barcode, []).append(p)
    if skus:
        dst_result = await dst_db.execute(select(Product).where(Product.sku.in_(skus)))
        for p in dst_result.scalars().all():
            dst_by_sku[p.sku] = p

    checks = []
    for product_id, quantity in merged.items():
        src = src_products.get(product_id)
        check = {
            "product_id": str(product_id),
            "product_name": src.name if src else None,
            "barcode": src.barcode if src else None,
            "quantity": quantity,
            "my_stock": (src.stock_level or 0) if src else 0,
            "dest_product_id": None,
            "dest_product_name": None,
            "dest_stock": None,
            "status": "ok",
            "message": "OK",
        }
        checks.append(check)

        def fail(message: str):
            check["status"] = "error"
            check["message"] = message

        if src is None:
            fail("Product not found")
            continue
        if quantity <= 0:
            fail("Quantity must be greater than 0")
            continue
        if not src.barcode:
            fail("This product has no barcode")
            continue

        matches = dst_by_barcode.get(src.barcode, [])
        if len(matches) > 1:
            fail(f"{len(matches)} products in {to_name} have this barcode")
            continue
        if not matches:
            same_sku = dst_by_sku.get(src.sku) if src.sku else None
            if same_sku is not None:
                fail(f"Barcode mismatch: {src.barcode} here, {same_sku.barcode or 'none'} in {to_name}")
            else:
                fail(f"Product not found in {to_name} (barcode {src.barcode})")
            continue

        dest = matches[0]
        check["dest_product_id"] = str(dest.id)
        check["dest_product_name"] = dest.name
        check["dest_stock"] = dest.stock_level or 0

        if quantity > (src.stock_level or 0):
            fail(f"Not enough stock (available: {src.stock_level or 0})")
            continue
        if not _same_name(src.name, dest.name):
            check["status"] = "warning"
            check["message"] = f"Name differs in {to_name}: '{dest.name}'"

    return checks


async def _is_duplicate(src_db: AsyncSession, merged: Dict[uuid.UUID, int]) -> bool:
    """Every item was already sent with the same qty seconds ago (double-click)"""
    cutoff = datetime.now() - timedelta(seconds=DUPLICATE_TRANSFER_WINDOW_SECONDS)
    for product_id, quantity in merged.items():
        result = await src_db.execute(
            select(StockEntry.id).where(
                StockEntry.product_id == product_id,
                StockEntry.location == TRANSFER_OUT,
                StockEntry.qty == -quantity,
                StockEntry.created_at >= cutoff,
            ).limit(1)
        )
        if result.first() is None:
            return False
    return True


async def _latest_vendors(db: AsyncSession, product_ids: List[uuid.UUID]) -> Dict[uuid.UUID, Vendor]:
    """Latest vendor of each product in this branch (same rule as the View Stock vendor column)"""
    if not product_ids:
        return {}
    result = await db.execute(
        select(StockEntry.product_id, Vendor)
        .join(Vendor, StockEntry.vendor_id == Vendor.id)
        .where(StockEntry.product_id.in_(product_ids))
        .order_by(StockEntry.product_id, StockEntry.created_at.desc())
        .distinct(StockEntry.product_id)
    )
    return {product_id: vendor for product_id, vendor in result.all()}


async def _invalidate_cache(branch_code: str) -> None:
    """Stock caches are namespaced by the current branch (utils/cache.py)"""
    from ..utils.cache import cache
    token = current_branch.set(branch_code)
    try:
        await cache.delete_pattern("stock:view:*")
        await cache.delete_pattern("product:barcode:*")
    except Exception:
        logger.warning("Stock cache invalidation failed for %s", branch_code, exc_info=True)
    finally:
        current_branch.reset(token)


async def save_transfer(
    src_db: AsyncSession, from_code: str, to_code: str, items: List[dict], user: User,
) -> dict:
    """Apply the transfer in both branches. Raises ShopTransferError (nothing
    changed) with `checks` attached when any item is blocked."""
    if not items:
        raise ShopTransferError("No items added")
    merged = _merge_items(items)
    factory = session_factories[to_code]

    async with factory() as dst_db:
        await src_db.execute(select(func.pg_advisory_xact_lock(SHOP_TRANSFER_LOCK_ID)))
        await dst_db.execute(select(func.pg_advisory_xact_lock(SHOP_TRANSFER_LOCK_ID)))

        if await _is_duplicate(src_db, merged):
            raise ShopTransferError("This transfer was already saved a moment ago")

        checks = await check_items(src_db, dst_db, to_code, items, lock=True)
        if any(c["status"] == "error" for c in checks):
            error = ShopTransferError("Some items cannot be transferred. Please review the highlighted items.")
            error.checks = checks
            raise error

        # Receiving branch has its own users table; match the sender by username
        dst_user = await dst_db.execute(select(User.id).where(User.username == user.username))
        dst_user_id = dst_user.scalar_one_or_none()

        now = datetime.now()
        out_ref = transfer_ref("TO", to_code, now)
        in_ref = transfer_ref("FROM", from_code, now)
        src_products = {p.id: p for p in (await src_db.execute(
            select(Product).where(Product.id.in_(list(merged)))
        )).scalars().all()}
        dst_ids = [uuid.UUID(c["dest_product_id"]) for c in checks]
        dst_products = {p.id: p for p in (await dst_db.execute(
            select(Product).where(Product.id.in_(dst_ids)).with_for_update()
        )).scalars().all()}

        # Vendor: the sending branch's vendor of the product; in the receiving branch the
        # vendor with the same name, else that product's own vendor there. No balance change.
        src_vendors = await _latest_vendors(db=src_db, product_ids=list(src_products))
        dst_vendors = await _latest_vendors(db=dst_db, product_ids=list(dst_products))
        src_vendor_names = {v.name for v in src_vendors.values()}
        dst_vendors_by_name = {}
        if src_vendor_names:
            dst_vendors_by_name = {v.name: v for v in (await dst_db.execute(
                select(Vendor).where(Vendor.name.in_(src_vendor_names))
            )).scalars().all()}

        out_entries = []
        for check in checks:
            src = src_products[uuid.UUID(check["product_id"])]
            dest = dst_products[uuid.UUID(check["dest_product_id"])]
            quantity = check["quantity"]
            src_vendor = src_vendors.get(src.id)
            dst_vendor = (dst_vendors_by_name.get(src_vendor.name) if src_vendor else None) or dst_vendors.get(dest.id)

            src.stock_level = (src.stock_level or 0) - quantity
            src.updated_at = now
            out_entry = StockEntry(
                product_id=src.id,
                vendor_id=src_vendor.id if src_vendor else None,
                qty=-quantity,
                cost_price=src.cost_price,
                unit_price=src.unit_price,
                type=StockEntryType.OUT,
                location=TRANSFER_OUT,
                ref=out_ref,
                created_by=user.id,
                created_at=now,
            )
            src_db.add(out_entry)
            out_entries.append(out_entry)

            # Only stock changes in the receiving branch; its price/name stay its own
            dest.stock_level = (dest.stock_level or 0) + quantity
            dest.updated_at = now
            dst_db.add(StockEntry(
                product_id=dest.id,
                vendor_id=dst_vendor.id if dst_vendor else None,
                qty=quantity,
                cost_price=src.cost_price,
                unit_price=dest.unit_price,
                type=StockEntryType.IN,
                location=TRANSFER_IN,
                ref=in_ref,
                created_by=dst_user_id,
                created_at=now,
            ))

        await src_db.flush()
        await dst_db.flush()
        await src_db.commit()

        try:
            await dst_db.commit()
        except Exception as e:
            logger.exception("Shop transfer %s -> %s failed in receiving DB, reversing", from_code, to_code)
            await _reverse_sending_side(src_db, checks, [entry.id for entry in out_entries], out_ref)
            raise ShopTransferError(
                f"Could not save in {BRANCHES[to_code].name}. The transfer was cancelled; please try again."
            ) from e

    await _invalidate_cache(from_code)
    await _invalidate_cache(to_code)

    return {
        "message": f"Stock transferred to {BRANCHES[to_code].name}",
        "to_branch": BRANCHES[to_code].name,
        "items": checks,
    }


async def _reverse_sending_side(
    src_db: AsyncSession, checks: List[dict], out_entry_ids: List[uuid.UUID], out_ref: str
) -> None:
    """Undo the committed sending side after the receiving DB failed."""
    try:
        await src_db.rollback()
        for check in checks:
            product = await src_db.get(
                Product, uuid.UUID(check["product_id"]), with_for_update=True, populate_existing=True
            )
            if product is not None:
                product.stock_level = (product.stock_level or 0) + check["quantity"]
                product.updated_at = datetime.now()
        await src_db.execute(delete(StockEntry).where(StockEntry.id.in_(out_entry_ids)))
        await src_db.commit()
    except Exception:
        # Sending branch is now short by the transfer qty with no matching Transfer In
        logger.critical("Shop transfer %s: reversing the sending side FAILED - fix stock manually", out_ref, exc_info=True)
        raise
