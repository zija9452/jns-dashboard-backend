"""
DTF logo printing - shared by Quotation and Customer Invoice.

A Hoodie / Jacket line (category with customer_categories.dtf_enabled) can carry an
optional `dtf` block: the size of each logo on one piece, and the layout the page
worked out - every print (logos x quantity) placed on a roll `roll_width_in` wide with
`gap_in` between prints. The roll length used is charged in 0.5 m steps
(`price_per_half_meter` each), with no tolerance: 0.5 m = 19.685", anything longer is 1 m.

The saved layout is what the designer follows (Invoice Details page), so the backend
doesn't re-pack it - it checks the layout is real: right number of prints, each the
size of its logo (or turned 90°), inside the roll, no two closer than the gap, and the
length / steps / charge match. `amount` is the charged amount, editable per order like
the mockup charge (0 = waived); `charge` is the roll-length price.

Item shape (JSON):
  "dtf": {
    "logos": [{"w": 4, "h": 4}, ...],              # inches, one piece
    "roll_width_in": 23, "gap_in": 0.5, "price_per_half_meter": 750,
    "layout": [{"x": 0, "y": 0, "w": 10, "h": 12, "logo": 1, "rotated": false}, ...],
    "length_in": 37.5, "half_meters": 2, "charge": 1500, "amount": 1500
  }
"""
import math
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.customer_category import CustomerCategory
from ..models.dtf_pricing import DtfPricingSetting

INCHES_PER_METER = 39.37
HALF_METER_IN = INCHES_PER_METER / 2   # 19.685"
MAX_LOGOS = 20
MAX_PRINTS = 5000
EPS = 0.01                             # layout numbers are rounded to 3 decimals by the page


def _bad(detail: str):
    raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=detail)


def _num(value, what: str) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        _bad(f"DTF: invalid {what}")
    if not math.isfinite(n):
        _bad(f"DTF: invalid {what}")
    return n


def half_meters_for(length_in: float) -> int:
    """0.5 m steps charged for a roll length - minimum one step, no tolerance."""
    return max(1, math.ceil(length_in / HALF_METER_IN - 1e-9))


async def load_dtf_context(db: AsyncSession, branch: str):
    """(names of DTF categories, this branch's DTF setting or None)."""
    result = await db.execute(select(CustomerCategory.main_category).where(CustomerCategory.dtf_enabled.is_(True)))
    names = set(result.scalars().all())
    setting_result = await db.execute(select(DtfPricingSetting).where(DtfPricingSetting.branch == branch))
    return names, setting_result.scalar_one_or_none()


def parse_item_dtf(raw, quantity: int, category: str, dtf_categories: Optional[set] = None,
                   setting: Optional[DtfPricingSetting] = None) -> Optional[dict]:
    """
    Validates one line's `dtf` block and returns it normalized, or None when the line
    has no DTF. On a new order pass `dtf_categories` and `setting` so the category must
    allow DTF and the rates must be the branch's current ones; on re-saving an existing
    order leave them None so the order keeps the rates it was made with.
    """
    if raw in (None, "", {}):
        return None
    if not isinstance(raw, dict):
        _bad("DTF: invalid data")
    if dtf_categories is not None and category not in dtf_categories:
        _bad(f"DTF logos are not allowed for {category}")

    roll = _num(raw.get("roll_width_in"), "roll width")
    gap = _num(raw.get("gap_in"), "gap")
    price = _num(raw.get("price_per_half_meter"), "rate")
    if roll <= 0 or gap < 0 or price < 0:
        _bad("DTF: invalid roll width, gap or rate")
    if setting is not None and (
        abs(roll - float(setting.roll_width_in)) > 1e-6
        or abs(gap - float(setting.gap_in)) > 1e-6
        or abs(price - float(setting.price_per_half_meter)) > 1e-6
    ):
        _bad("DTF rates were changed on the Ideal Pricing page - refresh the page and add the item again")

    logos_raw = raw.get("logos")
    if not isinstance(logos_raw, list) or not logos_raw:
        _bad(f"DTF: add at least one logo for {category}")
    if len(logos_raw) > MAX_LOGOS:
        _bad(f"DTF: at most {MAX_LOGOS} logos per item")
    logos = []
    for n, logo in enumerate(logos_raw, 1):
        if not isinstance(logo, dict):
            _bad("DTF: invalid logo")
        w = _num(logo.get("w"), f"width of logo {n}")
        h = _num(logo.get("h"), f"height of logo {n}")
        if w <= 0 or h <= 0:
            _bad(f"DTF: logo {n} needs a width and height")
        if min(w, h) > roll + EPS:
            _bad(f'DTF: logo {n} ({w:g}x{h:g}") is wider than the {roll:g}" roll even when turned')
        logos.append({"w": w, "h": h})

    expected_prints = len(logos) * quantity
    if expected_prints > MAX_PRINTS:
        _bad(f"DTF: {expected_prints} prints is more than the {MAX_PRINTS} allowed in one item")

    layout_raw = raw.get("layout")
    if not isinstance(layout_raw, list) or len(layout_raw) != expected_prints:
        _bad(f"DTF layout for {category} doesn't match {len(logos)} logo(s) x {quantity} pcs - add the item again")
    per_logo = [0] * len(logos)
    rects = []
    for p in layout_raw:
        if not isinstance(p, dict):
            _bad("DTF: invalid layout")
        idx = int(_num(p.get("logo"), "layout logo")) - 1
        if idx < 0 or idx >= len(logos):
            _bad("DTF: layout has an unknown logo")
        x, y = _num(p.get("x"), "layout position"), _num(p.get("y"), "layout position")
        w, h = _num(p.get("w"), "layout size"), _num(p.get("h"), "layout size")
        rotated = bool(p.get("rotated"))
        lw, lh = (logos[idx]["h"], logos[idx]["w"]) if rotated else (logos[idx]["w"], logos[idx]["h"])
        if abs(w - lw) > EPS or abs(h - lh) > EPS:
            _bad("DTF: layout size doesn't match the logo size")
        if x < -EPS or y < -EPS or x + w > roll + EPS:
            _bad("DTF: a logo is outside the roll")
        per_logo[idx] += 1
        rects.append({"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3),
                      "logo": idx + 1, "rotated": rotated})
    if any(c != quantity for c in per_logo):
        _bad(f"DTF layout must have each logo {quantity} times")

    # No two prints closer than the gap (sorted by top edge, so the inner loop stops early).
    rects_sorted = sorted(rects, key=lambda r: r["y"])
    for i, a in enumerate(rects_sorted):
        for b in rects_sorted[i + 1:]:
            if b["y"] >= a["y"] + a["h"] + gap - EPS:
                break
            apart = (
                a["x"] + a["w"] + gap <= b["x"] + EPS or b["x"] + b["w"] + gap <= a["x"] + EPS
                or a["y"] + a["h"] + gap <= b["y"] + EPS or b["y"] + b["h"] + gap <= a["y"] + EPS
            )
            if not apart:
                _bad(f'DTF: two logos are closer than the {gap:g}" gap - add the item again')

    length = max(r["y"] + r["h"] for r in rects)
    if abs(length - _num(raw.get("length_in"), "roll length")) > EPS:
        _bad("DTF: roll length doesn't match the layout")
    half_meters = half_meters_for(length)
    if int(_num(raw.get("half_meters"), "meters")) != half_meters:
        _bad("DTF: meters don't match the roll length")
    charge = half_meters * price
    if abs(_num(raw.get("charge"), "charge") - charge) > 0.5:
        _bad("DTF: charge doesn't match the roll length")

    amount = raw.get("amount", charge)
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        _bad(f"DTF: invalid amount for {category}")
    if amount < 0:
        _bad(f"DTF charge for {category} cannot be negative")

    return {
        "logos": logos,
        "roll_width_in": roll,
        "gap_in": gap,
        "price_per_half_meter": price,
        "layout": rects,
        "length_in": round(length, 3),
        "half_meters": half_meters,
        "charge": float(charge),
        "amount": float(amount),
    }


def dtf_charges_from_items(items_list: list) -> tuple[list, Decimal]:
    """Totals rows: one per line with DTF and a non-zero amount -> (charges, total)."""
    charges = []
    total = Decimal("0")
    for line, item in enumerate(items_list, 1):
        dtf = item.get("dtf")
        if not dtf or not dtf.get("amount"):
            continue
        charges.append({
            "line": line,
            "category": str(item.get("cat_name") or item.get("product_name") or ""),
            "meters": dtf["half_meters"] / 2,
            "amount": float(dtf["amount"]),
        })
        total += Decimal(str(dtf["amount"]))
    return charges, total


def dtf_charges_from_totals(totals: dict) -> list:
    """The saved list from a totals JSON (missing on orders saved before this feature)."""
    charges = totals.get("dtf_charges") or []
    return charges if isinstance(charges, list) else []
