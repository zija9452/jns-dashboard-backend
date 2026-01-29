from sqlmodel import SQLModel, Field, Relationship
from pydantic import condecimal
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid
import json
from enum import Enum

class Refund(SQLModel, table=True):
    __tablename__ = "refunds"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_id: uuid.UUID = Field(foreign_key="invoices.id")
    items: str = Field()  # JSON string for refunded items
    amount: Decimal = Field(decimal_places=2, max_digits=10)
    reason: str  # Text field for reason
    processed_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

class RefundRead(SQLModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    items: str
    amount: Decimal
    reason: str
    processed_by: uuid.UUID
    created_at: datetime

class RefundCreate(SQLModel):
    invoice_id: uuid.UUID
    items: str  # JSON string
    amount: Decimal
    reason: str
    processed_by: uuid.UUID

class RefundUpdate(SQLModel):
    items: Optional[str] = None
    amount: Optional[Decimal] = None
    reason: Optional[str] = None