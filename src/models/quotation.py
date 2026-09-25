from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric, Text
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
import uuid
from enum import Enum


class QuotationStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    APPROVED = "APPROVED"      # price locked - no further edits, ready to convert
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"    # already turned into a real Customer Order


class Quotation(SQLModel, table=True):
    __tablename__ = "quotations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quotation_no: str = Field(unique=True, index=True)  # "QUO-0001"
    customer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="customers.id", index=True)
    customer_name: Optional[str] = Field(default=None, index=True)
    team_name: Optional[str] = Field(default=None)
    salesman_id: Optional[uuid.UUID] = Field(default=None, foreign_key="salesmen.id", index=True)

    items: str = Field()   # JSON string, same shape as CustomerInvoice.items
    totals: str = Field()  # JSON string: subtotal, discount, rush_charge, tax, total

    total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), index=True))
    taxes: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    discounts: Optional[Decimal] = Field(default=0.00, sa_column=Column(Numeric(10, 2)))

    # Rush is derived from required_by_date, never a manual toggle. Rate/threshold are
    # snapshotted at save time so a later change to the global rush rule never
    # retroactively changes an already-sent/approved quotation's price.
    required_by_date: Optional[date] = Field(default=None, index=True)
    is_rush: bool = Field(default=False, index=True)
    rush_rate_snapshot: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    rush_threshold_snapshot: Optional[int] = Field(default=None)
    rush_charge: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))

    valid_until: Optional[date] = Field(default=None)  # quotation's own expiry (separate from required_by_date)
    status: QuotationStatus = Field(default=QuotationStatus.DRAFT, index=True)
    revision: int = Field(default=1)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    converted_invoice_id: Optional[uuid.UUID] = Field(default=None, foreign_key="customer_invoices.id")

    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)


class QuotationRead(SQLModel):
    id: uuid.UUID
    quotation_no: str
    customer_id: Optional[uuid.UUID]
    customer_name: Optional[str]
    team_name: Optional[str]
    salesman_id: Optional[uuid.UUID]
    items: str
    totals: str
    total_amount: Decimal
    taxes: Decimal
    discounts: Optional[Decimal]
    required_by_date: Optional[date]
    is_rush: bool
    rush_charge: Decimal
    valid_until: Optional[date]
    status: QuotationStatus
    revision: int
    notes: Optional[str]
    converted_invoice_id: Optional[uuid.UUID]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class QuotationCreate(SQLModel):
    customer_id: Optional[uuid.UUID] = None
    customer_name: Optional[str] = None
    team_name: Optional[str] = None
    salesman_id: Optional[uuid.UUID] = None
    items: str
    required_by_date: Optional[date] = None
    valid_until: Optional[date] = None
    discounts: Optional[Decimal] = 0.00
    notes: Optional[str] = None


class QuotationUpdate(SQLModel):
    items: Optional[str] = None
    required_by_date: Optional[date] = None
    valid_until: Optional[date] = None
    discounts: Optional[Decimal] = None
    notes: Optional[str] = None


class QuotationStatusUpdate(SQLModel):
    status: QuotationStatus
