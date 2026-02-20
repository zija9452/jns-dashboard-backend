from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid
import json

class Customer(SQLModel, table=True):
    __tablename__ = "customers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100, index=True)
    contacts: str = Field()  # JSON string for phone, email, address
    cnic: Optional[str] = Field(default=None, max_length=20)
    sal_id_fk: Optional[uuid.UUID] = Field(default=None)
    branch: Optional[str] = Field(default=None, max_length=200)
    cus_balance: Optional[Decimal] = Field(default=0.00, max_digits=10, decimal_places=2)  # Customer balance
    created_at: datetime = Field(default_factory=lambda: datetime.now(), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False, index=True)

class CustomerRead(SQLModel):
    id: uuid.UUID
    name: str
    contacts: str
    cnic: Optional[str]
    sal_id_fk: Optional[uuid.UUID]
    branch: Optional[str]
    cus_balance: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

class CustomerCreate(SQLModel):
    name: str
    contacts: str
    cnic: Optional[str] = None
    sal_id_fk: Optional[uuid.UUID] = None
    branch: Optional[str] = None
    cus_balance: Optional[Decimal] = 0.00

class CustomerUpdate(SQLModel):
    name: Optional[str] = None
    contacts: Optional[str] = None
    cnic: Optional[str] = None
    sal_id_fk: Optional[uuid.UUID] = None
    branch: Optional[str] = None
    cus_balance: Optional[Decimal] = None