from sqlmodel import SQLModel, Field, Relationship
from pydantic import condecimal
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
    invoice_no: str = Field(unique=True)  # Will be auto-generated
    customer_id: uuid.UUID = Field(foreign_key="customers.id")
    items: str = Field()  # JSON string for line items
    totals: str = Field()  # JSON string for subtotal, tax, total
    taxes: condecimal(decimal_places=2, max_digits=10) = Field(default=0.00)
    discounts: Optional[condecimal(decimal_places=2, max_digits=10)] = Field(default=0.00)
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT)
    payments: Optional[str] = Field(default="[]")  # JSON string for payment records
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

class InvoiceRead(SQLModel):
    id: uuid.UUID
    invoice_no: str
    customer_id: uuid.UUID
    items: str
    totals: str
    taxes: Decimal
    discounts: Optional[Decimal]
    status: InvoiceStatus
    payments: Optional[str]
    created_at: datetime
    updated_at: datetime

class InvoiceCreate(SQLModel):
    customer_id: uuid.UUID
    items: str  # JSON string
    totals: str  # JSON string
    taxes: Optional[Decimal] = 0.00
    discounts: Optional[Decimal] = 0.00
    status: Optional[InvoiceStatus] = InvoiceStatus.DRAFT

class InvoiceUpdate(SQLModel):
    items: Optional[str] = None
    totals: Optional[str] = None
    taxes: Optional[Decimal] = None
    discounts: Optional[Decimal] = None
    status: Optional[InvoiceStatus] = None
    payments: Optional[str] = None