"""
Designing / mockup charge - shared by Quotation and Customer Invoice.

A category (T-shirt, Short...) that has only 1-4 pcs in the order (single piece tier)
gets one mockup charge, once for that category, not per piece. The page sends the
amounts it shows (pre-filled from customer_categories.mockup_charge, editable per
order); the backend re-counts the pieces from the saved items and rejects a charge on a
category that is not in the order or already has 5+ pcs.
"""
import json
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status as http_status

# Same boundary as the pages' quantity tiers: 1-4 pcs = single piece rate.
MOCKUP_MAX_PIECES = 4


def _category_of(item: dict) -> str:
    return str(item.get("cat_name") or item.get("product_name") or "")


def parse_mockup_charges(raw, items_list: list) -> tuple[list, Decimal]:
    """
    raw: list (or JSON string of a list) of {"category": str, "amount": number}.
    items_list: the normalized items being saved (need "quantity" and "cat_name").
    Returns (charges, total) where charges = [{"category", "pieces", "amount"}], with
    0-amount entries dropped (a waived mockup isn't printed).
    """
    if raw in (None, "", []):
        return [], Decimal("0")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid mockup charges")
    if not isinstance(raw, list):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid mockup charges")

    pieces_by_category: dict = {}
    for item in items_list:
        cat = _category_of(item)
        pieces_by_category[cat] = pieces_by_category.get(cat, 0) + int(item.get("quantity", 0))

    charges = []
    seen = set()
    total = Decimal("0")
    for entry in raw:
        if not isinstance(entry, dict):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid mockup charges")
        category = str(entry.get("category") or "")
        try:
            amount = Decimal(str(entry.get("amount", 0)))
        except (InvalidOperation, ValueError):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid mockup charge for {category}")
        if amount < 0:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Mockup charge for {category} cannot be negative")
        if category in seen:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Mockup charge for {category} sent twice")
        seen.add(category)

        pieces = pieces_by_category.get(category, 0)
        if pieces == 0:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Mockup charge for {category}, but the order has no {category} items")
        if pieces > MOCKUP_MAX_PIECES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Mockup charge applies only to 1-{MOCKUP_MAX_PIECES} pcs - {category} has {pieces} pcs"
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
