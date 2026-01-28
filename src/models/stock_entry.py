from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime, date
import uuid
from enum import Enum

class StockEntryType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"

class StockEntry(SQLModel, table=True):
    __tablename__ = "stock_entries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id")
    qty: int  # Positive for IN, negative for OUT
    type: StockEntryType
    location: Optional[str] = Field(default=None, max_length=100)
    batch: Optional[str] = Field(default=None, max_length=50)
    expiry: Optional[date] = Field(default=None)
    ref: Optional[str] = Field(default=None)  # Reference to transaction
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StockEntryRead(SQLModel):
    id: uuid.UUID
    product_id: uuid.UUID
    qty: int
    type: StockEntryType
    location: Optional[str]
    batch: Optional[str]
    expiry: Optional[date]
    ref: Optional[str]
    created_at: datetime

class StockEntryCreate(SQLModel):
    product_id: uuid.UUID
    qty: int
    type: StockEntryType
    location: Optional[str] = None
    batch: Optional[str] = None
    expiry: Optional[date] = None
    ref: Optional[str] = None

class StockEntryUpdate(SQLModel):
    qty: Optional[int] = None
    type: Optional[StockEntryType] = None
    location: Optional[str] = None
    batch: Optional[str] = None
    expiry: Optional[date] = None
    ref: Optional[str] = None