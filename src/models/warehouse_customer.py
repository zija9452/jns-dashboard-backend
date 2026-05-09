from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid
import json

class WarehouseCustomer(SQLModel, table=True):
    __tablename__ = "warehouse_customers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100, index=True)
    contacts: str = Field()  # JSON string for phone, email, address
    cnic: Optional[str] = Field(default=None, max_length=20)
    branch: Optional[str] = Field(default=None, max_length=200)
    cus_balance: Optional[Decimal] = Field(default=0.00, max_digits=10, decimal_places=2)
    created_at: datetime = Field(default_factory=lambda: datetime.now(), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False, index=True)

class WarehouseCustomerRead(SQLModel):
    id: uuid.UUID
    name: str
    contacts: str
    cnic: Optional[str]
    branch: Optional[str]
    cus_balance: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

class WarehouseCustomerCreate(SQLModel):
    name: str
    contacts: str
    cnic: Optional[str] = None
    branch: Optional[str] = None
    cus_balance: Optional[Decimal] = 0.00

class WarehouseCustomerUpdate(SQLModel):
    name: Optional[str] = None
    contacts: Optional[str] = None
    cnic: Optional[str] = None
    branch: Optional[str] = None
    cus_balance: Optional[Decimal] = None
