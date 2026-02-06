from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Numeric
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid
import json
from enum import Enum

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_no: str = Field(unique=True, index=True)  # Auto-generated invoice number with index
    customer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="customers.id", index=True)  # For walk-in customers, this can be null
    salesman_id: Optional[uuid.UUID] = Field(default=None, foreign_key="salesmen.id", index=True)  # Salesman who processed the sale
    items: str = Field()  # JSON string for line items
    totals: str = Field()  # JSON string for subtotal, tax, total, etc.
    total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), index=True))  # Total order amount with index
    amount_paid: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))  # Amount received (will equal total for immediate payment)
    balance_due: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2), index=True))  # Balance due (0 for immediate payment with index)
    payment_status: str = Field(default="paid", index=True)  # Immediate payment will be "paid" instantly with index
    payments_history: str = Field(default="[]")  # JSON array of payment records
    taxes: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    discounts: Optional[Decimal] = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    status: InvoiceStatus = Field(default=InvoiceStatus.ISSUED, index=True)  # Use the invoice status enum with index
    payment_method: str = Field(default="cash", index=True)  # Payment method used with index
    notes: Optional[str] = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)  # Who created the invoice with index
    created_at: datetime = Field(default_factory=datetime.now, index=True)  # When created with index
    updated_at: datetime = Field(default_factory=datetime.now, index=True)  # Last updated with index

class InvoiceRead(SQLModel):
    id: uuid.UUID
    invoice_no: str
    customer_id: Optional[uuid.UUID]
    salesman_id: Optional[uuid.UUID]
    items: str
    totals: str
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    payment_status: str
    payments_history: str
    taxes: Decimal
    discounts: Optional[Decimal]
    status: InvoiceStatus
    payment_method: str
    notes: Optional[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

class InvoiceCreate(SQLModel):
    customer_id: Optional[uuid.UUID] = None  # Can be None for walk-in customers
    salesman_id: Optional[uuid.UUID] = None
    items: str  # JSON string
    totals: str  # JSON string
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    payment_status: str
    payments_history: Optional[str] = "[]"
    taxes: Optional[Decimal] = 0.00
    discounts: Optional[Decimal] = 0.00
    status: Optional[InvoiceStatus] = InvoiceStatus.ISSUED
    payment_method: Optional[str] = "cash"
    notes: Optional[str] = None

class InvoiceUpdate(SQLModel):
    items: Optional[str] = None
    totals: Optional[str] = None
    total_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    balance_due: Optional[Decimal] = None
    payment_status: Optional[str] = None
    payments_history: Optional[str] = None
    taxes: Optional[Decimal] = None
    discounts: Optional[Decimal] = None
    status: Optional[InvoiceStatus] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None