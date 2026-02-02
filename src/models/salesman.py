from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Numeric
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid

class Salesman(SQLModel, table=True):
    __tablename__ = "salesmen"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    code: str = Field(unique=True, max_length=20)
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=200)
    branch: Optional[str] = Field(default=None, max_length=50)
    commission_rate: Optional[Decimal] = Field(default=0.00, sa_column=Column(Numeric(5, 2), nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

class SalesmanRead(SQLModel):
    id: uuid.UUID
    name: str
    code: str
    phone: Optional[str] = None
    address: Optional[str] = None
    branch: Optional[str] = None
    commission_rate: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

class SalesmanCreate(SQLModel):
    name: str
    code: str
    phone: Optional[str] = None
    address: Optional[str] = None
    branch: Optional[str] = None
    commission_rate: Optional[Decimal] = 0.00

class SalesmanUpdate(SQLModel):
    name: Optional[str] = None
    code: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    branch: Optional[str] = None
    commission_rate: Optional[Decimal] = None