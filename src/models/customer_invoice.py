from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric, Text
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid
from enum import Enum
import sqlalchemy as sa


class CustomerInvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"


class CustomerInvoice(SQLModel, table=True):
    __tablename__ = "customer_invoices"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_no: str = Field(unique=True)  # Auto-generated invoice number
    customer_id: uuid.UUID = Field(foreign_key="customers.id")
    salesman_id: Optional[uuid.UUID] = Field(default=None, foreign_key="salesmen.id")
    items: str = Field()  # JSON string for line items (as per your JavaScript schema)
    totals: str = Field()  # JSON string for subtotal, tax, total, etc. (as per your JavaScript schema)
    total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))  # Total order amount
    amount_paid: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))  # Amount received so far
    balance_due: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))  # Remaining balance
    payment_status: str = Field(default="unpaid")  # "unpaid", "partial", "paid"
    payments_history: str = Field(default="[]")  # JSON array of payment records
    taxes: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    discounts: Optional[Decimal] = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    status: CustomerInvoiceStatus = Field(default=CustomerInvoiceStatus.ISSUED)  # DRAFT, ISSUED, PAID, CANCELLED
    payment_method: str = Field(default="cash")  # As per your JavaScript content
    notes: Optional[str] = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CustomerInvoiceRead(SQLModel):
    id: uuid.UUID
    invoice_no: str
    customer_id: uuid.UUID
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
    status: CustomerInvoiceStatus
    payment_method: str
    notes: Optional[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CustomerInvoiceCreate(SQLModel):
    customer_id: uuid.UUID
    salesman_id: Optional[uuid.UUID] = None
    items: str  # JSON string
    totals: str  # JSON string
    total_amount: Optional[Decimal] = 0.00
    amount_paid: Optional[Decimal] = 0.00
    balance_due: Optional[Decimal] = 0.00
    payment_status: Optional[str] = "unpaid"
    payments_history: Optional[str] = "[]"
    taxes: Optional[Decimal] = 0.00
    discounts: Optional[Decimal] = 0.00
    status: Optional[CustomerInvoiceStatus] = CustomerInvoiceStatus.ISSUED
    payment_method: Optional[str] = "cash"
    notes: Optional[str] = None


class CustomerInvoiceUpdate(SQLModel):
    items: Optional[str] = None
    totals: Optional[str] = None
    total_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    balance_due: Optional[Decimal] = None
    payment_status: Optional[str] = None
    payments_history: Optional[str] = None
    taxes: Optional[Decimal] = None
    discounts: Optional[Decimal] = None
    status: Optional[CustomerInvoiceStatus] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None