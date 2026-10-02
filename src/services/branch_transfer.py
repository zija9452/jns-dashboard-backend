"""
Warehouse -> branch stock transfer (MULTI_BRANCH_PLAN.md Phase 7).

The warehouse lives in the Light House database. A warehouse invoice for a
customer with `destination_branch` set (e.g. "european sports karimabad" ->
"karimabad") takes stock out of the warehouse in Light House, then adds it to
that branch's shop stock in the branch's own database.

Two databases cannot commit atomically, so the invoice is first committed with
transfer_status="pending" and flipped to "done" once the branch commit succeeds.
A failed transfer stays "pending" with transfer_error set and can be retried.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.branches import BRANCHES
from ..database.database import session_factories
from ..models.product import Product
from ..models.stock_entry import StockEntry, StockEntryType
from ..models.vendor import Vendor
from ..models.warehouse_invoice import WarehouseInvoice

logger = logging.getLogger(__name__)

# Serializes transfers inside the destination DB (transaction-scoped lock)
TRANSFER_LOCK_ID = 123462


class TransferError(Exception):
    """Transfer cannot be applied; message is shown to the user."""


async def transfer_invoice_stock(
    lh_db: AsyncSession, invoice_id: uuid.UUID, branch_code: str
) -> Tuple[Optional[str], Optional[str]]:
    """Apply a pending warehouse invoice to `branch_code`'s shop stock.

    The invoice row is locked (FOR UPDATE) so two retries can't both run.
    Returns (transfer_status, transfer_error) after the attempt.
    """
    result = await lh_db.execute(
        select(WarehouseInvoice)
        .where(WarehouseInvoice.id == invoice_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    invoice = result.scalar_one_or_none()
    if invoice is None or invoice.transfer_status != "pending":
        await lh_db.rollback()
        return (invoice.transfer_status if invoice else None), None

    try:
        await _apply_in_branch(lh_db, invoice, branch_code)
        invoice.transfer_status = "done"
        invoice.transfer_error = None
    except Exception as e:
        logger.exception("Warehouse transfer %s -> %s failed", invoice.invoice_no, branch_code)
        invoice.transfer_error = (str(e) or type(e).__name__)[:1000]

    invoice.updated_at = datetime.now()
    lh_db.add(invoice)
    await lh_db.commit()
    return invoice.transfer_status, invoice.transfer_error


async def _apply_in_branch(lh_db: AsyncSession, invoice: WarehouseInvoice, branch_code: str) -> None:
    factory = session_factories.get(branch_code)
    if factory is None:
        raise TransferError(f"Branch '{branch_code}' database is not configured")
    branch = BRANCHES[branch_code]

    items = json.loads(invoice.items or "[]")
    lh_ids = [uuid.UUID(i["product_id"]) for i in items]
    lh_result = await lh_db.execute(select(Product).where(Product.id.in_(lh_ids)))
    lh_products = {p.id: p for p in lh_result.scalars().all()}

    async with factory() as db:
        await db.execute(select(func.pg_advisory_xact_lock(TRANSFER_LOCK_ID)))

        # Idempotency: an earlier attempt may have committed here while the
        # Light House "done" update failed.
        already = await db.execute(
            select(StockEntry.id).where(StockEntry.ref == invoice.invoice_no).limit(1)
        )
        if already.first():
            logger.info("Warehouse transfer %s already applied in %s", invoice.invoice_no, branch_code)
            return

        vendor_result = await db.execute(select(Vendor).where(Vendor.name == "J&S Sports"))
        vendor = vendor_result.scalars().first()

        now = datetime.now()
        for item in items:
            lh_product = lh_products.get(uuid.UUID(item["product_id"]))
            if lh_product is None:
                raise TransferError(f"Product '{item.get('product_name')}' not found in warehouse")
            if not lh_product.barcode:
                raise TransferError(f"Product '{lh_product.name}' has no barcode")

            # Match by barcode (names can differ between branches)
            result = await db.execute(select(Product).where(Product.barcode == lh_product.barcode))
            product = result.scalar_one_or_none()
            if product is None:
                product = await _create_branch_product(db, lh_product, branch.name, now)

            quantity = int(item["quantity"])
            product.stock_level = (product.stock_level or 0) + quantity
            product.updated_at = now
            db.add(product)

            db.add(StockEntry(
                product_id=product.id,
                qty=quantity,
                type=StockEntryType.IN,
                location="Stock In",
                vendor_id=vendor.id if vendor else None,
                ref=invoice.invoice_no,
            ))

        await db.commit()


async def _create_branch_product(db: AsyncSession, src: Product, branch_name: str, now: datetime) -> Product:
    """First transfer of a product the branch doesn't have yet: copy it with
    stock 0 and no warehouse fields. Price is only copied here; later transfers
    never overwrite the branch's own price."""
    sku_taken = await db.execute(select(Product.id).where(Product.sku == src.sku).limit(1))
    if sku_taken.first():
        raise TransferError(
            f"SKU '{src.sku}' already used by another product in {branch_name} (barcode differs)"
        )
    id_taken = await db.get(Product, src.id)

    product = Product(
        id=uuid.uuid4() if id_taken else src.id,
        sku=src.sku,
        name=src.name,
        unit_price=src.unit_price,
        cost_price=src.cost_price,
        stock_level=0,
        attributes=src.attributes,
        barcode=src.barcode,
        discount=src.discount,
        category=src.category,
        branch=branch_name,
        limited_qty=src.limited_qty,
        brand_action=src.brand_action,
        is_warehouse_product=False,
        article_no=src.article_no,
        warehouse_stock=0,
        warehouse_cost=src.warehouse_cost or 0,
        warehouse_limited_qty=0,
        created_at=now,
        updated_at=now,
    )
    db.add(product)
    await db.flush()
    return product
