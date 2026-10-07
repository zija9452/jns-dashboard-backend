"""
Designing / mockup charge - shared by Quotation and Customer Invoice.

A category (T-shirt, Short...) that has only 1-4 pcs in the order (single piece tier)
gets one mockup charge, once for that category, not per piece. The page sends the
amounts it shows (pre-filled from customer_categories.mockup_charge, editable per
order); the backend re-counts the pieces from the saved items and rejects a charge on a
category that is not in the order or already has 5+ pcs.

Dye lines (an option ticked "Dye" on the Customer Category page - sub-category
dye_options) never bring the charge - the page raises their rate instead (the
category's dye_rate_single / dye_rate_qty) - so a category with only dye pieces is
rejected too.
"""
import json
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.customer_category import CustomerCategory

# Same boundary as the pages' quantity tiers: 1-4 pcs = single piece rate.
MOCKUP_MAX_PIECES = 4


def _category_of(item: dict) -> str:
    return str(item.get("cat_name") or item.get("product_name") or "")


async def load_dye_options(db: AsyncSession) -> dict:
    """{main_category: {sub_category: set of dye options}} for the current branch DB."""
    result = await db.execute(select(CustomerCategory.main_category, CustomerCategory.sub_categories))
    dye_map: dict = {}
    for main_category, sub_categories in result.all():
        for sc in sub_categories or []:
            dye = set(sc.get("dye_options") or [])
            if dye:
                dye_map.setdefault(main_category, {})[sc.get("sub_category")] = dye
    return dye_map


def _is_dye(item: dict, dye_options: dict) -> bool:
    """Same rule as isDyeLine on the pages: a selected option is ticked as dye."""
    category_dye = dye_options.get(_category_of(item))
    if not category_dye:
        return False
    fields = item.get("category_fields") or {}
    if isinstance(fields, str):
        try:
            fields = json.loads(fields or "{}")
        except (json.JSONDecodeError, TypeError):
            return False
    if not isinstance(fields, dict):
        return False
    return any(fields.get(sub) in options for sub, options in category_dye.items())


def parse_mockup_charges(raw, items_list: list, dye_options: dict | None = None) -> tuple[list, Decimal]:
    """
    raw: list (or JSON string of a list) of {"category": str, "amount": number}.
    items_list: the normalized items being saved (need "quantity", "cat_name" and
    "category_fields").
    dye_options: from load_dye_options().
    Returns (charges, total) where charges = [{"category", "pieces", "amount"}], with
    0-amount entries dropped (a waived mockup isn't printed).
    """
    if raw in (None, "", []):
        return [], Decimal("0")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid flat charges")
    if not isinstance(raw, list):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid flat charges")

    dye_options = dye_options or {}
    pieces_by_category: dict = {}
    non_dye_by_category: dict = {}
    for item in items_list:
        cat = _category_of(item)
        qty = int(item.get("quantity", 0))
        pieces_by_category[cat] = pieces_by_category.get(cat, 0) + qty
        if not _is_dye(item, dye_options):
            non_dye_by_category[cat] = non_dye_by_category.get(cat, 0) + qty

    charges = []
    seen = set()
    total = Decimal("0")
    for entry in raw:
        if not isinstance(entry, dict):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid flat charges")
        category = str(entry.get("category") or "")
        try:
            amount = Decimal(str(entry.get("amount", 0)))
        except (InvalidOperation, ValueError):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid flat charges for {category}")
        if amount < 0:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Flat charges for {category} cannot be negative")
        if category in seen:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Flat charges for {category} sent twice")
        seen.add(category)

        pieces = pieces_by_category.get(category, 0)
        if pieces == 0:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Flat charges for {category}, but the order has no {category} items")
        if pieces > MOCKUP_MAX_PIECES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Flat charges apply only to 1-{MOCKUP_MAX_PIECES} pcs - {category} has {pieces} pcs"
            )
        if amount > 0 and non_dye_by_category.get(category, 0) == 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"No flat charges on dye - {category} has only dye pieces (dye rate applies instead)"
            )
        if amount == 0:
            continue
        charges.append({"category": category, "pieces": pieces, "amount": float(amount)})
        total += amount

    return charges, total


def mockup_charges_from_totals(totals: dict) -> list:
    """The saved list from a totals JSON (missing on orders saved before this feature)."""
    charges = totals.get("mockup_charges") or []
    return charges if isinstance(charges, list) else []
