from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Numeric
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
import uuid
import json

class WarehouseInvoice(SQLModel, table=True):
    __tablename__ = "warehouse_invoices"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_no: str = Field(index=True, unique=True)
    customer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="warehouse_customers.id")
    customer_name: Optional[str] = None
    items: str = Field(default="[]")  # JSON string of items
    totals: str = Field(default="{}")  # JSON string of totals
    total_amount: Decimal = Field(default=0.0, sa_column=Column(Numeric(10, 2)))
    amount_paid: Decimal = Field(default=0.0, sa_column=Column(Numeric(10, 2)))
    payment_status: Optional[str] = "paid"
    payments_history: Optional[str] = "[]"
    discounts: Decimal = Field(default=0.0, sa_column=Column(Numeric(10, 2)))
    payment_method: Optional[str] = "cash"
    payment_date: Optional[datetime] = Field(default_factory=datetime.now)
    notes: Optional[str] = None
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class WarehouseInvoiceRead(SQLModel):
    id: uuid.UUID
    invoice_no: str
    customer_id: Optional[uuid.UUID]
    customer_name: Optional[str]
    items: str
    totals: str
    total_amount: Decimal
    amount_paid: Decimal
    payment_status: Optional[str]
    payment_method: Optional[str]
    payment_date: Optional[datetime]
    notes: Optional[str]
    created_by: uuid.UUID
    created_at: datetime
