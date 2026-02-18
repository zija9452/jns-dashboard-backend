from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Numeric
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid
import json
from pydantic import ConfigDict

class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sku: str = Field(unique=True, max_length=50)
    name: str = Field(max_length=100)
    unit_price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    cost_price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    stock_level: int = Field(default=0)
    attributes: Optional[str] = Field(default=None)  # JSON string for extensibility
    barcode: Optional[str] = Field(default=None, unique=True, max_length=50)
    discount: Optional[Decimal] = Field(default=0.00, sa_column=Column(Numeric(5, 2), nullable=True))
    category: Optional[str] = Field(default=None, max_length=50)
    branch: Optional[str] = Field(default=None, max_length=50)
    limited_qty: int = Field(default=0)  # Keep this field as requested
    brand_action: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)


class ProductRead(SQLModel):
    id: uuid.UUID
    sku: str
    name: str
    unit_price: Decimal
    cost_price: Decimal
    stock_level: int
    attributes: Optional[str]
    barcode: Optional[str]
    discount: Optional[Decimal]
    category: Optional[str]
    branch: Optional[str]
    limited_qty: int
    brand_action: Optional[str]
    created_at: datetime
    updated_at: datetime


class ProductCreate(SQLModel):
    sku: str
    name: str
    unit_price: Decimal
    cost_price: Decimal
    stock_level: int = 0
    attributes: Optional[str] = None
    barcode: Optional[str] = None
    discount: Optional[Decimal] = 0.00
    category: Optional[str] = None
    branch: Optional[str] = None
    limited_qty: int = 0
    brand_action: Optional[str] = None


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    unit_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    stock_level: Optional[int] = None
    attributes: Optional[str] = None
    barcode: Optional[str] = None
    discount: Optional[Decimal] = None
    category: Optional[str] = None
    branch: Optional[str] = None
    limited_qty: Optional[int] = None
    brand_action: Optional[str] = None

    model_config = ConfigDict(json_encoders={Decimal: float})