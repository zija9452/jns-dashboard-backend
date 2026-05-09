from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import Column, Numeric, Text
from decimal import Decimal

class WarehouseVendor(SQLModel, table=True):
    __tablename__ = "warehouse_vendors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    contacts: str = Field()  # JSON string for phone, email, address
    branch: Optional[str] = Field(default=None, max_length=200)
    terms: Optional[str] = Field(default=None)  # JSON string for payment terms
    balance: Optional[Decimal] = Field(default=0.00, sa_column=Column(Numeric(10, 2), nullable=True))
    payments_history: Optional[str] = Field(default="[]", sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

class WarehouseVendorRead(SQLModel):
    id: uuid.UUID
    name: str
    contacts: str
    branch: Optional[str]
    terms: Optional[str]
    balance: Optional[Decimal]
    payments_history: Optional[str]
    created_at: datetime
    updated_at: datetime

class WarehouseVendorCreate(SQLModel):
    name: str
    contacts: str  # JSON string
    branch: Optional[str] = None
    terms: Optional[str] = None  # JSON string
    balance: Optional[Decimal] = 0.00

class WarehouseVendorUpdate(SQLModel):
    name: Optional[str] = None
    contacts: Optional[str] = None
    branch: Optional[str] = None
    terms: Optional[str] = None
    balance: Optional[Decimal] = None
    payments_history: Optional[str] = None
