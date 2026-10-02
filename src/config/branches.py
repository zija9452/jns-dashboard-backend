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
    invoice_prefix: str  # Prepended to SIN-/CIN-/QUO- numbers ("" keeps Light House numbering unchanged)
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
        invoice_prefix="",
        barcode_prefix="690",
        contact="0315-2263745",
        address="Shop#8, Mazar Wali Gali, Light House, Khi",
    ),
    "karimabad": Branch(
        code="karimabad",
        name="European Sports Karim Abad",
        db_env="DATABASE_URL_KARIMABAD",
        invoice_prefix="K",
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
    """Number prefix for the current branch: doc_prefix("SIN") -> "SIN-" in
    Light House, "KSIN-" in Karim Abad. doc_type: SIN, CIN, QUO."""
    return f"{this_branch().invoice_prefix}{doc_type}-"


def get_branch(code: Optional[str]) -> Optional[Branch]:
    return BRANCHES.get(code) if code else None


def configured_branches() -> List[Branch]:
    """Branches whose database URL is set in the environment."""
    return [b for b in BRANCHES.values() if b.database_url]
