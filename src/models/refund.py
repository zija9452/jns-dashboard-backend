from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Numeric
from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import field_validator
import uuid
import json
from enum import Enum

class Refund(SQLModel, table=True):
    __tablename__ = "refunds"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_id: uuid.UUID = Field(foreign_key="invoices.id", index=True)  # Index for JOIN performance
    invoice_no: str = Field(default="N/A", index=True)  # Store invoice number directly for performance
    items: str = Field()  # JSON string for refunded items
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    reason: str  # Text field for reason
    processed_by: uuid.UUID = Field(foreign_key="users.id", index=True)  # Index for user filtering
    created_at: datetime = Field(default_factory=datetime.now, index=True)  # Index for date filtering
    updated_at: datetime = Field(default_factory=datetime.now, index=True)  # Index for sorting

class RefundRead(SQLModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    items: str
    amount: Decimal
    reason: str
    processed_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

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
    created_at: Optional[datetime] = None  # Allow updating the date of the refund
    updated_at: Optional[datetime] = None

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def normalize_datetime(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            # Parse ISO string and convert to UTC, removing timezone info
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            # Convert to naive datetime in UTC
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        if isinstance(v, datetime) and v.tzinfo is not None:
            # Convert timezone-aware to naive UTC
            return v.replace(tzinfo=None)
        return v