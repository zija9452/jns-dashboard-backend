from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Numeric
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid
import json

class Customer(SQLModel, table=True):
    __tablename__ = "customers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    contacts: str = Field()  # JSON string for phone, email, etc.
    billing_addr: Optional[str] = Field(default=None)  # JSON string for address
    shipping_addr: Optional[str] = Field(default=None)  # JSON string for address
    credit_limit: Optional[Decimal] = Field(default=0.00, sa_column=Column(Numeric(10, 2), nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

class CustomerRead(SQLModel):
    id: uuid.UUID
    name: str
    contacts: str
    billing_addr: Optional[str]
    shipping_addr: Optional[str]
    credit_limit: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

class CustomerCreate(SQLModel):
    name: str
    contacts: str  # JSON string
    billing_addr: Optional[str] = None  # JSON string
    shipping_addr: Optional[str] = None  # JSON string
    credit_limit: Optional[Decimal] = 0.00

class CustomerUpdate(SQLModel):
    name: Optional[str] = None
    contacts: Optional[str] = None
    billing_addr: Optional[str] = None
    shipping_addr: Optional[str] = None
    credit_limit: Optional[Decimal] = None