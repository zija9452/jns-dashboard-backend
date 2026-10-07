"""
Branch (shop) registry.

Each branch has its own database; the code is shared. The selected branch is
carried in the `branch` cookie (set at login) and `get_db()` routes every
request to that branch's database.
"""
import os
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Branch:
    code: str  # Value stored in the `branch` cookie
    name: str  # Display name (login dropdown, top bar)
    db_env: str  # Env var holding this branch's DATABASE_URL
    # Document number prefixes (a "-" and the 4-digit number follow). Each must not be
    # the start of another one + "-", since reports filter by LIKE '<prefix>-%'.
    walkin_prefix: str     # walk-in sale (SIN)
    customer_prefix: str   # customer invoice / order (CIN)
    quotation_prefix: str  # quotation (QUO)
    deposit_prefix: str    # cash deposit to bank (DEP)
    barcode_prefix: str  # First 3 digits of generated barcodes; differs per branch so two shops never print the same barcode
    contact: str = ""  # Receipt header phone; empty -> line not printed
    address: str = ""  # Receipt header address; empty -> line not printed

    @property
    def database_url(self) -> Optional[str]:
        return os.getenv(self.db_env) or None


BRANCHES: Dict[str, Branch] = {
    "lighthouse": Branch(
        code="lighthouse",
        name="European Sports Light House",
        db_env="DATABASE_URL",
        walkin_prefix="SIN",
        customer_prefix="CIN",
        quotation_prefix="QUO",
        deposit_prefix="DEP",
        barcode_prefix="690",
        contact="0315-2263745",
        address="Shop#8, Mazar Wali Gali, Light House, Khi",
    ),
    "karimabad": Branch(
        code="karimabad",
        name="European Sports Karim Abad",
        db_env="DATABASE_URL_KARIMABAD",
        # 2026-10-02: EK-0001 walk-in, EKC-0001 customer order (were KSIN- / KCIN-, no KA invoices yet)
        walkin_prefix="EK",
        customer_prefix="EKC",
        quotation_prefix="KQUO",
        deposit_prefix="KDEP",
        barcode_prefix="691",
        # TEMP (2026-10-02): Light House contact/address until the manager confirms Karim Abad's
        contact="0315-2263745",
        address="Shop#8, Mazar Wali Gali, Light House, Khi",
    ),
}

# Requests without a branch cookie (e.g. sessions created before multi-branch)
# keep working against Light House.
DEFAULT_BRANCH = "lighthouse"
BRANCH_COOKIE = "branch"

# Branch of the request being served; set by get_db(). Used where there is no
# request object (cache keys, Firestore signal ids).
current_branch: ContextVar[str] = ContextVar("current_branch", default=DEFAULT_BRANCH)


def this_branch() -> Branch:
    """Branch of the request being served."""
    return BRANCHES[current_branch.get()]


def current_branch_name() -> str:
    """Display name of the request's branch; also the value stored in the
    `branch` columns (products, expenses, customers, ...)."""
    return this_branch().name


def doc_prefix(doc_type: str) -> str:
    """Number prefix for the current branch. doc_type: SIN (walk-in), CIN (customer
    invoice), QUO (quotation), DEP (cash deposit). Light House: SIN- / CIN- / QUO- / DEP-;
    Karim Abad: EK- / EKC- / KQUO- / KDEP-."""
    branch = this_branch()
    prefixes = {
        "SIN": branch.walkin_prefix,
        "CIN": branch.customer_prefix,
        "QUO": branch.quotation_prefix,
        "DEP": branch.deposit_prefix,
    }
    return f"{prefixes[doc_type]}-"


def get_branch(code: Optional[str]) -> Optional[Branch]:
    return BRANCHES.get(code) if code else None


def configured_branches() -> List[Branch]:
    """Branches whose database URL is set in the environment."""
    return [b for b in BRANCHES.values() if b.database_url]
