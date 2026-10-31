"""
Batch barcode + price helpers (BATCH_COSTING_PLAN.md).

Batch barcode = product barcode + vendor code (3+ digits) + batch no (3+ digits), e.g.
690001998 + 001 + 001 = 690001998001001. Scanning one finds its product even where the
batch is not known yet (sales, other branch): the product is the longest product
barcode the scanned code starts with, followed by at least 6 more digits.
"""
from decimal import Decimal, ROUND_CEILING
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.product import Product

BATCH_SUFFIX_MIN = 6  # vendor code (3) + batch no (3)


def make_batch_barcode(product_barcode: str, vendor_code: str, batch_no: int) -> str:
    return f"{product_barcode}{vendor_code}{batch_no:03d}"


def round_up_to_10(amount: Decimal) -> Decimal:
    """71 -> 80, 70.22 -> 80, 70 -> 70."""
    return (amount / 10).to_integral_value(rounding=ROUND_CEILING) * 10


def batch_prices(cost: Decimal, invoice_total: Decimal, freight: Decimal, cartage: Decimal,
                 markup_pct: Decimal) -> Tuple[Decimal, Decimal]:
    """(landed cost, selling price): cost + freight % + cartage % of the invoice; markup %
    is on the cost only (not on freight / cartage), rounded up to 10."""
    extra = (freight + cartage) / invoice_total if invoice_total else Decimal("0")
    landed = cost * (1 + extra)
    # To paisa first (same as the Stock In page), so 70.004 is 70 and not 80
    selling = round_up_to_10((landed + cost * markup_pct / 100).quantize(Decimal("0.01")))
    return landed.quantize(Decimal("0.01")), selling


async def product_for_batch_barcode(db: AsyncSession, code: Optional[str]) -> Optional[Product]:
    """Product of a scanned batch barcode, or None when `code` is not one (a normal
    product barcode, a name, ...)."""
    code = (code or "").strip()
    if not code.isdigit() or len(code) <= BATCH_SUFFIX_MIN:
        return None
    if (await db.execute(select(Product.id).where(Product.barcode == code).limit(1))).first():
        return None  # an ordinary product barcode
    prefixes = [code[:n] for n in range(1, len(code) - BATCH_SUFFIX_MIN + 1)]
    result = await db.execute(select(Product).where(Product.barcode.in_(prefixes)))
    products = result.scalars().all()
    return max(products, key=lambda p: len(p.barcode)) if products else None


async def search_term_for(db: AsyncSession, term: Optional[str]) -> Optional[str]:
    """For product search boxes: a scanned batch barcode becomes its product barcode."""
    product = await product_for_batch_barcode(db, term)
    return product.barcode if product else term
