from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid
from ..config.branches import current_branch_name

# Plain VARCHAR (not Postgres enums) so new values need no ALTER TYPE.
PROOF_MISSING = "MISSING"    # Online payment recorded, no screenshot yet
PROOF_PENDING = "PENDING"    # Screenshot uploaded, waiting for sales/admin
PROOF_APPROVED = "APPROVED"  # Money confirmed - locked
PROOF_REJECTED = "REJECTED"  # Money not received (invoice unchanged); a new pay slip resubmits it -> PENDING

SOURCE_CUSTOMIZED = "CUSTOMIZED"  # customer_invoices
SOURCE_WALKIN = "WALKIN"          # invoices (walk-in bills)

# Methods that need no screenshot; every other method is an online payment.
OFFLINE_METHODS = {"", "cash", "credit", "other"}


def is_online_method(method: Optional[str]) -> bool:
    return (method or "").strip().lower() not in OFFLINE_METHODS


class PaymentProof(SQLModel, table=True):
    """Screenshot proof of one online payment (Easypaisa / bank) of an invoice.
    Created with the payment (MISSING); images can be added later."""
    __tablename__ = "payment_proofs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source: str = Field(default=SOURCE_CUSTOMIZED, max_length=20, index=True)
    invoice_id: uuid.UUID = Field(index=True)  # customer_invoices.id (CUSTOMIZED) or invoices.id (WALKIN); no FK
    invoice_no: str = Field(max_length=50, index=True)
    customer_name: Optional[str] = Field(default=None, max_length=255)
    payment_id: str = Field(max_length=36)  # "id" of the entry in the invoice's payments_history
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    payment_method: str = Field(max_length=50)
    payment_date: datetime
    status: str = Field(default=PROOF_MISSING, max_length=20, index=True)
    recorded_by: uuid.UUID = Field(foreign_key="users.id")
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(), index=True)
    uploaded_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    uploaded_at: Optional[datetime] = None
    reviewed_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = None
    reject_reason: Optional[str] = Field(default=None, max_length=500)
    branch: str = Field(max_length=100, default_factory=current_branch_name, index=True)


class PaymentProofImage(SQLModel, table=True):
    """One screenshot of a payment proof (original quality on Cloudinary)."""
    __tablename__ = "payment_proof_images"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    proof_id: uuid.UUID = Field(foreign_key="payment_proofs.id", index=True)
    file_url: str = Field(max_length=500)
    public_id: Optional[str] = Field(default=None, max_length=255)  # For Cloudinary delete


class PaymentProofReject(SQLModel):
    reason: str
