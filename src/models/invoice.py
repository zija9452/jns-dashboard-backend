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
    invoice_no: str = Field(unique=True, index=True)  # Auto-generated invoice number with index (format: SIN-0001, SIN-0002, etc.)
    customer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="customers.id", index=True)  # Customer ID with FK reference (optional)
    customer_name: str = Field(default="Walk-in Customer", index=True)  # Name of customer
    salesman_id: Optional[uuid.UUID] = Field(default=None, foreign_key="salesmen.id", index=True)  # Salesman ID with FK reference (optional)
    items: str = Field()  # JSON string for line items (includes product_id for each item)
    totals: str = Field()  # JSON string for subtotal, tax, total, etc.
    total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), index=True))  # Total order amount with index
    amount_paid: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))  # Amount received
    payment_status: str = Field(default="paid", index=True)  # Payment status - always "paid" for walk-in
    payments_history: str = Field(default="[]")  # JSON array of payment records
    discounts: Optional[Decimal] = Field(default=0.00, sa_column=Column(Numeric(10, 2)))  # Total discount amount
    payment_method: str = Field(default="cash", index=True)  # Payment method used with index
    payment_date: datetime = Field(default_factory=datetime.now, index=True)  # Payment date with index
    notes: Optional[str] = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)  # Who created the invoice with index
    created_at: datetime = Field(default_factory=datetime.now, index=True)  # When created with index
    updated_at: datetime = Field(default_factory=datetime.now, index=True)  # Last updated with index

class InvoiceRead(SQLModel):
    id: uuid.UUID
    invoice_no: str
    customer_id: Optional[uuid.UUID]  # Customer ID with FK reference
    customer_name: str  # Name of customer
    salesman_id: Optional[uuid.UUID]  # Salesman ID with FK reference
    items: str
    totals: str
    total_amount: Decimal
    amount_paid: Decimal
    payment_status: str
    payments_history: str
    discounts: Optional[Decimal]
    payment_method: str
    payment_date: datetime
    notes: Optional[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

class InvoiceCreate(SQLModel):
    customer_id: Optional[uuid.UUID] = None  # Customer ID with FK reference (optional)
    customer_name: str = "Walk-in Customer"  # Name of customer (default: "Walk-in Customer")
    salesman_id: Optional[uuid.UUID] = None  # Salesman ID with FK reference (optional)
    items: str  # JSON string (includes product_id for each item)
    totals: str  # JSON string
    total_amount: Decimal
    amount_paid: Decimal
    payment_status: str = "paid"
    payments_history: Optional[str] = "[]"
    discounts: Optional[Decimal] = 0.00
    payment_method: Optional[str] = "cash"
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None

class InvoiceUpdate(SQLModel):
    customer_id: Optional[uuid.UUID] = None  # Customer ID with FK reference
    customer_name: Optional[str] = None  # Name of customer
    salesman_id: Optional[uuid.UUID] = None  # Salesman ID with FK reference
    items: Optional[str] = None
    totals: Optional[str] = None
    total_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    payment_status: Optional[str] = None
    payments_history: Optional[str] = None
    discounts: Optional[Decimal] = None
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None