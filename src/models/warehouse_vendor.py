from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import Column, Numeric, Text
from decimal import Decimal

def vendor_code_for(vendor_no: int) -> str:
    """Vendor code that goes into batch barcodes (product + vendor code + batch no).
    1-899 -> 001-899; then 9000-9899, 99000-99899 ... A shorter code never starts with
    9 and a longer one always starts with one more 9, so no code is the start of
    another and a barcode always splits one way."""
    if vendor_no < 900:
        return f"{vendor_no:03d}"
    nines, value = divmod(vendor_no - 900, 900)
    return "9" * (nines + 1) + f"{value:03d}"


class WarehouseVendor(SQLModel, table=True):
    __tablename__ = "warehouse_vendors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)  # unique, ignoring case / outer spaces
    vendor_no: Optional[int] = Field(default=None, unique=True)  # 1, 2, 3 ... never reused
    vendor_code: Optional[str] = Field(default=None, max_length=10, unique=True)  # vendor_no as barcode digits, see vendor_code_for
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
    vendor_code: Optional[str] = None
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
