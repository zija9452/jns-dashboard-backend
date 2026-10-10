"""
A product added in one branch is also created in the other branches with the same
barcode / SKU / name / price and stock 0, so one label scans in every shop.

Only the creation is copied: later edits (price, name...), stock and deletes stay per
branch. Warehouse products are not copied (they reach a branch by warehouse transfer,
see branch_transfer.py) and neither are "(dummy)" display pieces.
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select

from ..config.branches import BRANCHES, configured_branches, current_branch
from ..database.database import session_factories
from ..models.product import Product

logger = logging.getLogger(__name__)


def should_mirror(is_warehouse_product: bool, name: str) -> bool:
    return not is_warehouse_product and "DUMMY" not in (name or "").upper()


def _other_branches() -> List[str]:
    here = current_branch.get()
    return [b.code for b in configured_branches() if b.code != here and b.code in session_factories]


async def find_clash(name: str, sku: str, barcode: Optional[str]) -> Optional[str]:
    """Error message if the copy could not be made in another branch: there the name
    or SKU belongs to a product with a different barcode. A product with the same
    barcode there is the same product - nothing to copy, no clash."""
    for code in _other_branches():
        async with session_factories[code]() as db:
            if barcode:
                same = await db.execute(select(Product.id).where(Product.barcode == barcode).limit(1))
                if same.first():
                    continue
            result = await db.execute(
                select(Product.name, Product.sku).where(
                    (func.lower(Product.name) == (name or "").lower()) | (Product.sku == sku)
                ).limit(1)
            )
            row = result.first()
            if row:
                what = "name" if row.name.lower() == (name or "").lower() else "SKU"
                return f"{BRANCHES[code].name} already has a product with this {what} ('{row.name}') but a different barcode"
    return None


async def mirror_product(src: Product) -> List[str]:
    """Create `src` with stock 0 in the other branches that don't have its barcode.
    Returns warnings for branches where it failed (the product stays in this branch;
    running sync_products.py later fills the gap)."""
    warnings: List[str] = []
    if not src.barcode or not should_mirror(src.is_warehouse_product, src.name):
        return warnings
    for code in _other_branches():
        branch = BRANCHES[code]
        try:
            async with session_factories[code]() as db:
                exists = await db.execute(select(Product.id).where(Product.barcode == src.barcode).limit(1))
                if exists.first():
                    continue
                db.add(copy_for_branch(src, branch.name, keep_id=not await db.get(Product, src.id)))
                await db.commit()
        except Exception as e:
            logger.exception("Copying product %s to %s failed", src.barcode, code)
            warnings.append(f"Not added in {branch.name}: {str(e) or type(e).__name__}"[:300])
    return warnings


def copy_for_branch(src, branch_name: str, keep_id: bool = True) -> Product:
    """Shop product with stock 0 in another branch; `src` is a Product or a DB row."""
    now = datetime.now()
    return Product(
        id=src.id if keep_id else uuid.uuid4(),
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
        warehouse_cost=0,
        warehouse_limited_qty=0,
        created_at=now,
        updated_at=now,
    )
