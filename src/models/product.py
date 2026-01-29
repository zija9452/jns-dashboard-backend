from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid
import json

class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sku: str = Field(unique=True, max_length=50)
    name: str = Field(max_length=100)
    desc: Optional[str] = Field(default=None)
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)
    cost_price: Decimal = Field(max_digits=10, decimal_places=2)
    tax_rate: Optional[Decimal] = Field(default=0.00, max_digits=5, decimal_places=2)
    vendor_id: Optional[uuid.UUID] = Field(default=None, foreign_key="vendors.id")
    stock_level: int = Field(default=0)
    attributes: Optional[str] = Field(default=None)  # JSON string for extensibility
    barcode: Optional[str] = Field(default=None, unique=True, max_length=50)
    discount: Optional[Decimal] = Field(default=0.00, max_digits=5, decimal_places=2)
    category: Optional[str] = Field(default=None, max_length=50)
    branch: Optional[str] = Field(default=None, max_length=50)
    limited_qty: bool = Field(default=False)
    brand_action: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

class ProductRead(SQLModel):
    id: uuid.UUID
    sku: str
    name: str
    desc: Optional[str]
    unit_price: Decimal
    cost_price: Decimal
    tax_rate: Optional[Decimal]
    vendor_id: Optional[uuid.UUID]
    stock_level: int
    attributes: Optional[str]
    barcode: Optional[str]
    discount: Optional[Decimal]
    category: Optional[str]
    branch: Optional[str]
    limited_qty: bool
    brand_action: Optional[str]
    created_at: datetime
    updated_at: datetime

class ProductCreate(SQLModel):
    sku: str
    name: str
    desc: Optional[str] = None
    unit_price: Decimal
    cost_price: Decimal
    tax_rate: Optional[Decimal] = 0.00
    vendor_id: Optional[uuid.UUID] = None
    stock_level: int = 0
    attributes: Optional[str] = None
    barcode: Optional[str] = None
    discount: Optional[Decimal] = 0.00
    category: Optional[str] = None
    branch: Optional[str] = None
    limited_qty: bool = False
    brand_action: Optional[str] = None

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    desc: Optional[str] = None
    unit_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    vendor_id: Optional[uuid.UUID] = None
    stock_level: Optional[int] = None
    attributes: Optional[str] = None
    barcode: Optional[str] = None
    discount: Optional[Decimal] = None
    category: Optional[str] = None
    branch: Optional[str] = None
    limited_qty: Optional[bool] = None
    brand_action: Optional[str] = None