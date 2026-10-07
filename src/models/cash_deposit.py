from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
import uuid
from ..config.branches import current_branch_name

# Status is plain VARCHAR (not a Postgres enum) so new values need no ALTER TYPE.
DEPOSIT_PENDING = "PENDING"
DEPOSIT_APPROVED = "APPROVED"  # Locked: no edit / approve / reject after this
DEPOSIT_REJECTED = "REJECTED"  # Cashier edits and resubmits -> PENDING again


class CashDeposit(SQLModel, table=True):
    """Cash in hand taken to the bank. One deposit can cover several days
    (cash_from -> cash_to, info only) and have several bank slips."""
    __tablename__ = "cash_deposits"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    deposit_no: str = Field(max_length=20, unique=True, index=True)  # DEP-0001 / KDEP-0001
    cash_from: date
    cash_to: date
    deposit_date: date = Field(default_factory=date.today, index=True)
    total_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))  # Sum of slip amounts
    notes: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(default=DEPOSIT_PENDING, max_length=20, index=True)
    submitted_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(), index=True)
    reviewed_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = None
    reject_reason: Optional[str] = Field(default=None, max_length=500)
    branch: str = Field(max_length=100, default_factory=current_branch_name, index=True)


class CashDepositSlip(SQLModel, table=True):
    """One bank slip image of a deposit (original quality on Cloudinary)."""
    __tablename__ = "cash_deposit_slips"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    deposit_id: uuid.UUID = Field(foreign_key="cash_deposits.id", index=True)
    file_url: str = Field(max_length=500)
    public_id: Optional[str] = Field(default=None, max_length=255)  # For Cloudinary delete
    bank_name: str = Field(max_length=100)
    slip_no: Optional[str] = Field(default=None, max_length=100)
    amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))


class CashDepositSlipRead(SQLModel):
    id: uuid.UUID
    file_url: str
    bank_name: str
    slip_no: Optional[str] = None
    amount: Decimal


class CashDepositRead(SQLModel):
    id: uuid.UUID
    deposit_no: str
    cash_from: date
    cash_to: date
    deposit_date: date
    total_amount: Decimal
    notes: Optional[str] = None
    status: str
    submitted_by: uuid.UUID
    submitted_by_name: Optional[str] = None
    submitted_at: datetime
    reviewed_by: Optional[uuid.UUID] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    branch: str
    slips: List[CashDepositSlipRead] = []


# Create / Update arrive as multipart form (fields + slip images), so these
# schemas hold the non-file part; slip files are matched to SlipInfo by order.
class CashDepositSlipInfo(SQLModel):
    bank_name: str
    slip_no: Optional[str] = None
    amount: Decimal


class CashDepositCreate(SQLModel):
    cash_from: date
    cash_to: date
    deposit_date: date
    notes: Optional[str] = None
    slips: List[CashDepositSlipInfo]


class CashDepositUpdate(SQLModel):
    cash_from: Optional[date] = None
    cash_to: Optional[date] = None
    deposit_date: Optional[date] = None
    notes: Optional[str] = None
    remove_slip_ids: List[uuid.UUID] = []  # Existing slips to delete
    new_slips: List[CashDepositSlipInfo] = []  # Matched to the uploaded files by order


class CashDepositReject(SQLModel):
    reason: str
