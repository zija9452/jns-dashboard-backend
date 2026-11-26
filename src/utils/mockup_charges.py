"""
Designing / mockup charge - shared by Quotation and Customer Invoice.

NOW (TEAM_MOQ_PLAN.md, 2026-11-26): ONE MOQ per team, from all its pieces together -
1-4 pcs with one category, 1-9 pcs with 2+ categories, none when all pieces are dye.
The entry still names the category it sits on; new entries carry "scope": "team".
The notes below describe the older per-category rule (old saved orders).

A category (T-shirt, Short...) that has only 1-4 pcs in the order (single piece tier)
gets one mockup charge, once for that category, not per piece. The page sends the
amounts it shows (pre-filled from customer_categories.mockup_charge, editable per
order); the backend re-counts the pieces from the saved items and rejects a charge on a
category that is not in the order or already has 5+ pcs.

Dye lines (an option ticked "Dye" on the Customer Category page - sub-category
dye_options) never bring the charge - the page raises their rate instead (the
category's dye_rate_single / dye_rate_qty) - so a category with only dye pieces is
rejected too.

Teams: a quotation can hold several teams (item "team"). The pieces are then counted
per team and category - Team A with 3 T-shirts and Team B with 2 T-shirts each get
their own charge - and each entry carries its "team". Items and entries without a team
(Customer Invoice page, older orders) all count as one team, so they work as before.
"""
import json
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.customer_category import CustomerCategory

# Same boundary as the pages' quantity tiers: 1-4 pcs = single piece rate.
MOCKUP_MAX_PIECES = 4
# Team MOQ: a team with 2+ categories has its one MOQ at 1-9 pcs (all categories together).
TEAM_MOQ_MAX_MULTI = 9


def team_moq_limit(category_count: int) -> int:
    """1-4 pcs with one category in the team, 1-9 pcs with more (same as the pages)."""
    return TEAM_MOQ_MAX_MULTI if category_count > 1 else MOCKUP_MAX_PIECES


def moq_print_label(mc: dict, with_team: bool = False) -> str:
    """'MOQ Charges' for a team MOQ (scope "team"), 'MOQ Charges - T-shirt' for an older
    per-category one. with_team adds the team name for a list outside the team's block."""
    from html import escape
    team = team_of(mc)
    if mc.get("scope") == "team":
        return f"MOQ Charges - {escape(team)}" if with_team and team else "MOQ Charges"
    category = escape(str(mc.get("category", "")))
    return f"MOQ Charges - {escape(team)} - {category}" if with_team and team else f"MOQ Charges - {category}"


def _category_of(item: dict) -> str:
    return str(item.get("cat_name") or item.get("product_name") or "")


def team_of(item: dict) -> str:
    """The item's (or charge entry's) team; "" = no team (the whole order as one)."""
    return str(item.get("team") or "").strip()


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


def parse_mockup_charges(raw, items_list: list, dye_options: dict | None = None,
                         user=None, previous: list | None = None) -> tuple[list, Decimal]:
    """
    raw: list (or JSON string of a list) of {"category": str, "amount": number}, plus
    "team" when the items have teams.
    items_list: the normalized items being saved (need "quantity", "cat_name",
    "category_fields" and, for a team order, "team").
    dye_options: from load_dye_options().
    user: the logged-in user saving the order (recorded on a waived / reduced charge).
    previous: the charges saved before (edit / revision) - an unchanged waived / reduced
    charge keeps the name of whoever changed it first.
    Returns (charges, total) where charges = [{"category", "pieces", "amount"}] (+ "team"
    when set). An entry may carry "default_amount" (what the page worked out). When the
    amount is below it, the entry is kept - even at 0 - with "default_amount", "change"
    ("waived" = 0, "reduced" = less) and "changed_by" / "changed_by_id", so staff can see
    it on the View pages. Prints leave the 0 ones out (see printed_mockup_charges). A 0
    without a higher default (no MOQ, free kit line) is dropped as before.
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
    # Team MOQ (TEAM_MOQ_PLAN.md): pieces counted per team, all categories together;
    # team "" = items without a team. (team, category) pieces only check the entry's
    # category is in that team.
    pieces_by_key: dict = {}
    team_pieces: dict = {}
    team_non_dye: dict = {}
    team_categories: dict = {}
    for item in items_list:
        team = team_of(item)
        key = (team, _category_of(item))
        qty = int(item.get("quantity", 0))
        pieces_by_key[key] = pieces_by_key.get(key, 0) + qty
        team_pieces[team] = team_pieces.get(team, 0) + qty
        team_categories.setdefault(team, set()).add(key[1])
        if not _is_dye(item, dye_options):
            team_non_dye[team] = team_non_dye.get(team, 0) + qty

    charges = []
    seen = set()
    total = Decimal("0")
    for entry in raw:
        if not isinstance(entry, dict):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid flat charges")
        category = str(entry.get("category") or "")
        team = team_of(entry)
        key = (team, category)
        label = f"{team} - {category}" if team else category
        try:
            amount = Decimal(str(entry.get("amount", 0)))
        except (InvalidOperation, ValueError):
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid flat charges for {label}")
        if amount < 0:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Flat charges for {label} cannot be negative")
        if key in seen:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Flat charges for {label} sent twice")
        seen.add(key)

        if pieces_by_key.get(key, 0) == 0:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Flat charges for {label}, but the order has no {label} items")
        pieces = team_pieces.get(team, 0)
        limit = team_moq_limit(len(team_categories.get(team, ())))
        team_label = team or "the order"
        if pieces > limit:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"MOQ charges apply only to 1-{limit} pcs - {team_label} has {pieces} pcs"
            )
        if amount > 0 and team_non_dye.get(team, 0) == 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"No MOQ charges on dye - {team_label} has only dye pieces (dye rate applies instead)"
            )
        default_amount = _default_amount_of(entry, label)
        lowered = default_amount is not None and amount < default_amount
        if amount == 0 and not lowered:
            continue
        # scope "team" = one MOQ for the team's pieces (older entries: per category).
        charge = {"category": category, "pieces": pieces, "amount": float(amount), "scope": "team"}
        if team:
            charge["team"] = team
        if lowered:
            charge["default_amount"] = float(default_amount)
            charge["change"] = "waived" if amount == 0 else "reduced"
            charge.update(_changed_by(previous, key, amount, default_amount, user))
        charges.append(charge)
        total += amount

    return charges, total


def _default_amount_of(entry: dict, label: str) -> Decimal | None:
    """The page's own amount for this charge, or None when not sent (older pages)."""
    raw = entry.get("default_amount")
    if raw in (None, ""):
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Invalid flat charges for {label}")
    return value if value > 0 else None


def _changed_by(previous: list | None, key: tuple, amount: Decimal, default_amount: Decimal, user) -> dict:
    """Who lowered the charge: the earlier name when the same change was already saved,
    otherwise the user saving now. Never taken from the page's data."""
    for old in previous or []:
        if not isinstance(old, dict) or (team_of(old), str(old.get("category") or "")) != key:
            continue
        try:
            same = (Decimal(str(old.get("amount", 0))) == amount
                    and Decimal(str(old.get("default_amount", -1))) == default_amount)
        except (InvalidOperation, ValueError):
            same = False
        if same and old.get("changed_by"):
            return {"changed_by": old.get("changed_by"), "changed_by_id": old.get("changed_by_id")}
    if user is None:
        return {}
    return {
        # username is the person's own name (Suleman); full_name is often just the role ("cashier").
        "changed_by": getattr(user, "username", None) or getattr(user, "full_name", None) or "",
        "changed_by_id": str(getattr(user, "id", "") or ""),
    }


def printed_mockup_charges(totals: dict) -> list:
    """The saved charges for a printed bill / quotation: waived (0) ones are left out and
    the staff-only fields are dropped - the customer sees only what is charged."""
    staff_only = ("default_amount", "change", "changed_by", "changed_by_id")
    return [
        {k: v for k, v in mc.items() if k not in staff_only}
        for mc in mockup_charges_from_totals(totals)
        if isinstance(mc, dict) and float(mc.get("amount", 0) or 0) > 0
    ]


def mockup_charges_from_totals(totals: dict) -> list:
    """The saved list from a totals JSON (missing on orders saved before this feature)."""
    charges = totals.get("mockup_charges") or []
    return charges if isinstance(charges, list) else []
