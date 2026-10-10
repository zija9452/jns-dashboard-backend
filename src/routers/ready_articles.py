"""
Ready articles for the Team Name search on Quotation / Customer Invoice.

Products are stored one per size ("BRAZIL 2023 SHORTS M", "BRAZIL 2023 L"). Here the size
and the words Jersey / Shorts / Trouser are taken off the name and products are grouped
by what is left - the team ("BRAZIL 2023") - with the kit kinds we have for it, taken
from the product's category name (FOOTBALL JERSEY -> jersey, DYE SHORT -> short...).
A team that is one of these articles gets the kit flat (see lib/quantityPricing.ts).
"""
import re

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.session_auth import employee_order_booker_required_from_session
from ..database.database import get_db
from ..models.product import Product
from ..models.user import User

router = APIRouter(prefix="/ready-articles", tags=["Ready Articles"])

# Kind by the product category's name; the first match wins.
KIND_WORDS = (("jersey", "JERSEY"), ("short", "SHORT"), ("trouser", "TROUSER"))
KIND_ORDER = ["jersey", "short", "trouser"]

# Sizes: XS..4XL (also "(S)"), kids "4Y" / "12 y". Not after "/" - "F/S" is full sleeve.
SIZE = re.compile(r"(?<!/)\(?\b(?:XXS|XS|S|M|L|XL|XXL|XXXL|[2-5]XL|\d{1,2}\s?Y)\b\)?", re.IGNORECASE)
KIND_WORD = re.compile(r"\b(?:JERSEYS?|SHORTS?|TROUSERS?)\b", re.IGNORECASE)
EDGE_JUNK = re.compile(r"^[\s/\-().,]+|[\s/\-(.,]+$")


def article_name(product_name: str) -> str:
    """'BRAZIL 2023 SHORTS M' -> 'BRAZIL 2023' (upper case, single spaces)."""
    name = SIZE.sub(" ", product_name or "")
    name = KIND_WORD.sub(" ", name)
    name = " ".join(name.split())
    return EDGE_JUNK.sub("", name).upper()


def kind_of(category: str | None) -> str | None:
    upper = (category or "").upper()
    return next((kind for kind, word in KIND_WORDS if word in upper), None)


@router.get("")
async def list_ready_articles(
    current_user: User = Depends(employee_order_booker_required_from_session()),
    db: AsyncSession = Depends(get_db),
):
    """[{"name": "BRAZIL 2023", "kinds": ["jersey", "short"]}, ...] sorted by name."""
    result = await db.execute(select(Product.name, Product.category))
    kinds_by_name: dict[str, set] = {}
    for name, category in result.all():
        # "(dummy)" display pieces are not articles a customer orders
        if "DUMMY" in (name or "").upper():
            continue
        kind = kind_of(category)
        if not kind:
            continue
        article = article_name(name)
        if len(article) < 2:
            continue
        kinds_by_name.setdefault(article, set()).add(kind)
    data = [
        {"name": name, "kinds": [k for k in KIND_ORDER if k in kinds]}
        for name, kinds in sorted(kinds_by_name.items())
    ]
    return {"data": data}
