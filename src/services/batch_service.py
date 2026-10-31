"""
Stocking products into a batch (BATCH_COSTING_PLAN.md): a batch is one lot, each vendor
inside it (BatchVendor) has its own bill / freight / cartage / markup.
"""
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.branches import DEFAULT_BRANCH, current_branch
from ..database.database import resolve_branch_code
from ..models.batch import Batch, BatchVendor, ProductBatch, BATCH_OPEN
from ..models.product import Product
from ..models.stock_entry import StockEntry, StockEntryType
from ..models.warehouse_vendor import WarehouseVendor
from ..utils.batch_barcode import make_batch_barcode, batch_prices


def light_house_only(request: Request):
    """Warehouse batches live in the Light House DB: logged into another branch, the batch
    pages / batch Stock In refuse instead of making batches in that branch's DB."""
    if resolve_branch_code(request) != DEFAULT_BRANCH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Batches are kept in Light House (warehouse) - switch to Light House")


def batch_label(vendor: WarehouseVendor, batch: Batch) -> str:
    code = f" ({vendor.vendor_code})" if vendor.vendor_code else ""
    return f"{vendor.name.strip()}{code} - Batch {batch.batch_no:03d}"


def line_label(batch: Batch, vendor: Optional[WarehouseVendor] = None) -> str:
    """"Batch 001" under the product name on invoices / copies - no vendor (user, 31-10);
    two vendors' lines of one batch differ by their barcode."""
    return f"Batch {batch.batch_no:03d}"


async def product_batch_label(db: AsyncSession, product_batch: ProductBatch) -> str:
    """"Batch 001" in Light House, the copied label in another branch."""
    batch = await db.get(Batch, product_batch.batch_id) if product_batch.batch_id else None
    if not batch:
        return product_batch.label or ""
    batch_vendor = await db.get(BatchVendor, product_batch.batch_vendor_id) if product_batch.batch_vendor_id else None
    vendor = await db.get(WarehouseVendor, batch_vendor.warehouse_vendor_id) if batch_vendor else None
    return line_label(batch, vendor)


async def open_batch_vendor(db: AsyncSession, batch_id: str, vendor_id: Optional[UUID]) -> Tuple[Batch, BatchVendor]:
    """The batch a Stock In goes into: must exist and be OPEN, and the chosen vendor must
    be in it (its bill / freight / cartage / markup added first)."""
    if current_branch.get() != DEFAULT_BRANCH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Batches are kept in Light House (warehouse) - switch to Light House")
    try:
        batch = await db.get(Batch, UUID(batch_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid batch ID format")
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    if batch.status != BATCH_OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This batch is closed - choose an open batch")
    batch_vendor = (await db.execute(
        select(BatchVendor).where(BatchVendor.batch_id == batch.id, BatchVendor.warehouse_vendor_id == vendor_id)
    )).scalar_one_or_none()
    if not batch_vendor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Add this vendor's bill to Batch {batch.batch_no:03d} first")
    return batch, batch_vendor


async def stock_into_batch(db: AsyncSession, product: Product, batch: Batch, batch_vendor: BatchVendor,
                           vendor: WarehouseVendor, qty: int, cost: Decimal,
                           selling_price: Optional[Decimal]) -> Tuple[ProductBatch, bool]:
    """Add qty of product to its line of this vendor in batch (made on the first Stock In,
    with the batch barcode). Cost / price are the latest entered. selling_price None =
    worked out from the vendor's bill in the batch (cost + freight % + cartage % + markup %
    of cost, rounded up to 10). The caller updates product.warehouse_stock, writes the
    stock entry and commits.
    Returns (line, True if the line was made now - to copy to the other branches)."""
    if not product.barcode:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{product.name} has no barcode")
    if not vendor.vendor_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Vendor {vendor.name.strip()} has no code")

    landed, worked_out = batch_prices(cost, batch_vendor.invoice_total, batch_vendor.freight,
                                      batch_vendor.cartage, batch_vendor.markup_pct)
    price = selling_price if selling_price and selling_price > 0 else worked_out

    line = (await db.execute(
        select(ProductBatch).where(ProductBatch.product_id == product.id, ProductBatch.batch_vendor_id == batch_vendor.id)
    )).scalar_one_or_none()
    is_new = line is None
    if not line:
        barcode = make_batch_barcode(product.barcode, vendor.vendor_code, batch.batch_no)
        # Never two items with one barcode (a product's own, or another batch line's)
        taken = (await db.execute(select(Product.name).where(Product.barcode == barcode).limit(1))).scalar_one_or_none()
        if not taken:
            other = (await db.execute(
                select(Product.name).join(ProductBatch, ProductBatch.product_id == Product.id)
                .where(ProductBatch.barcode == barcode).limit(1)
            )).scalar_one_or_none()
            taken = f"{other} (another batch)" if other else None
        if taken:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Barcode {barcode} already belongs to {taken} - not saved",
            )
        line = ProductBatch(product_id=product.id, batch_id=batch.id, batch_vendor_id=batch_vendor.id,
                            barcode=barcode, cost=cost, landed_cost=landed, selling_price=price, warehouse_stock=0)

    line.cost = cost
    line.landed_cost = landed
    line.selling_price = price
    line.warehouse_stock = (line.warehouse_stock or 0) + qty
    line.updated_at = datetime.now()
    db.add(line)
    await db.flush()
    return line, is_new


async def bills_in_use(db: AsyncSession, batch_vendor_ids: List[UUID]) -> set:
    """Vendor bills with stock in them: their figures are locked, as the prices (and labels)
    of that stock were worked out from them."""
    if not batch_vendor_ids:
        return set()
    result = await db.execute(
        select(ProductBatch.batch_vendor_id).where(ProductBatch.batch_vendor_id.in_(batch_vendor_ids)).distinct()
    )
    return {row[0] for row in result.all()}


async def stocked_totals(db: AsyncSession, batch_vendor_ids: List[UUID]) -> Dict[UUID, Decimal]:
    """Bill amount stocked in so far per vendor in a batch (qty x cost of its Stock In
    entries), for "Stocked 4,80,000 / 5,00,000"."""
    if not batch_vendor_ids:
        return {}
    result = await db.execute(
        select(ProductBatch.batch_vendor_id, func.coalesce(func.sum(StockEntry.qty * StockEntry.cost_price), 0))
        .join(StockEntry, StockEntry.product_batch_id == ProductBatch.id)
        .where(ProductBatch.batch_vendor_id.in_(batch_vendor_ids), StockEntry.type == StockEntryType.IN)
        .group_by(ProductBatch.batch_vendor_id)
    )
    totals = {b: Decimal("0") for b in batch_vendor_ids}
    totals.update({row[0]: Decimal(str(row[1])) for row in result.all()})
    return totals


async def line_ranges(db: AsyncSession, rows: List[Tuple[UUID, int, Decimal, Decimal]], shop: bool) -> Dict[UUID, dict]:
    """Lowest / highest cost, price and margin % over each product's lines - its Old Stock
    (while not 0) and every batch - so a list shows "1,000 – 2,000" on the product row.
    rows: (product id, stock, cost, price) as the list has them, warehouse or shop (`shop`).
    Only products with batches are returned."""
    if not rows:
        return {}
    result = await db.execute(select(ProductBatch).where(ProductBatch.product_id.in_([r[0] for r in rows])))
    batches: Dict[UUID, List[ProductBatch]] = {}
    for pb in result.scalars().all():
        batches.setdefault(pb.product_id, []).append(pb)

    ranges = {}
    for product_id, stock, cost, price in rows:
        if product_id not in batches:
            continue
        if shop:
            # The shop's own rate / price from the warehouse invoice, else the batch's
            lines = [(pb.stock_level or 0,
                      pb.shop_cost if pb.shop_cost is not None else pb.cost,
                      pb.shop_price if pb.shop_price is not None else pb.selling_price)
                     for pb in batches[product_id]]
        else:
            lines = [(pb.warehouse_stock or 0, pb.cost, pb.selling_price) for pb in batches[product_id]]
        if (stock or 0) - sum(line[0] for line in lines) != 0:
            lines.append((0, cost or 0, price or 0))  # Old Stock
        costs = [float(c) for _, c, _ in lines]
        prices = [float(p) for _, _, p in lines]
        margins = [round((float(p) - float(c)) / float(c) * 100, 2) if c else 0.0 for _, c, p in lines]
        ranges[product_id] = {
            "cost": [min(costs), max(costs)],
            "price": [min(prices), max(prices)],
            "margin": [min(margins), max(margins)],
        }
    return ranges
