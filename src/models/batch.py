from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric, UniqueConstraint
from typing import Optional
from decimal import Decimal
from datetime import date, datetime
import uuid

# Plain VARCHAR (not Postgres enums) so new values need no ALTER TYPE.
BATCH_OPEN = "OPEN"      # Goods of this bill still arriving - shown in Stock In
BATCH_CLOSED = "CLOSED"  # All goods arrived - locked

LOCATION_WAREHOUSE = "warehouse"


class Batch(SQLModel, table=True):
    """One lot (laat) reaching the warehouse: Batch 001, 002 ... numbered once for the
    whole warehouse, with any number of vendors inside (BatchVendor). Lives in the Light
    House DB (warehouse)."""
    __tablename__ = "batches"
    __table_args__ = (UniqueConstraint("location", "batch_no", name="ux_batches_location_batch_no"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    location: str = Field(default=LOCATION_WAREHOUSE, max_length=20, index=True)
    batch_no: int
    batch_date: date
    status: str = Field(default=BATCH_OPEN, max_length=10, index=True)
    note: Optional[str] = Field(default=None, max_length=500)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    closed_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    closed_at: Optional[datetime] = None


class BatchVendor(SQLModel, table=True):
    """One vendor inside one batch: that vendor's bill of the lot. Its freight / cartage /
    markup apply to every item of the vendor stocked in under the batch. Added at Stock In
    when the vendor's goods of the lot arrive."""
    __tablename__ = "batch_vendors"
    __table_args__ = (UniqueConstraint("batch_id", "warehouse_vendor_id", name="ux_batch_vendors_batch_vendor"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    batch_id: uuid.UUID = Field(foreign_key="batches.id", index=True)
    warehouse_vendor_id: uuid.UUID = Field(foreign_key="warehouse_vendors.id", index=True)
    bill_date: Optional[date] = None  # day this vendor's goods of the lot arrived
    invoice_total: Decimal = Field(sa_column=Column(Numeric(14, 2), nullable=False))
    freight: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(12, 2), nullable=False))
    cartage: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(12, 2), nullable=False))
    markup_pct: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(6, 2), nullable=False))
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class BatchImage(SQLModel, table=True):
    """One picture of a vendor's bill in a batch (original quality on Cloudinary)."""
    __tablename__ = "batch_images"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    batch_id: uuid.UUID = Field(foreign_key="batches.id", index=True)
    batch_vendor_id: Optional[uuid.UUID] = Field(default=None, foreign_key="batch_vendors.id", index=True)
    file_url: str = Field(max_length=500)
    public_id: Optional[str] = Field(default=None, max_length=255)  # For Cloudinary delete


class BatchCreate(SQLModel):
    batch_date: date
    note: Optional[str] = None


class BatchUpdate(SQLModel):
    batch_date: Optional[date] = None
    note: Optional[str] = None



class ProductBatch(SQLModel, table=True):
    """One product of one vendor inside one batch: its own barcode (product barcode +
    vendor code + batch no), cost, price and stock, so old stock keeps its old price. The
    product's warehouse_stock stays the total of all its batches + old (unbatched) stock."""
    __tablename__ = "product_batches"
    __table_args__ = (UniqueConstraint("product_id", "batch_vendor_id", name="ux_product_batches_product_batch_vendor"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True)
    # None in another branch's DB: a copy of a Light House batch line, made by a warehouse invoice
    batch_id: Optional[uuid.UUID] = Field(default=None, foreign_key="batches.id", index=True)
    batch_vendor_id: Optional[uuid.UUID] = Field(default=None, foreign_key="batch_vendors.id", index=True)
    label: Optional[str] = Field(default=None, max_length=100)  # "Batch 001" on such a copy
    barcode: str = Field(max_length=50, unique=True)
    cost: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))  # vendor bill cost
    landed_cost: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))  # cost + freight % + cartage %
    selling_price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    warehouse_stock: int = Field(default=0)
    stock_level: int = Field(default=0)  # shop stock, from warehouse invoices
    shop_cost: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2), nullable=True))  # last invoice rate
    shop_price: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2), nullable=True))  # shop selling price
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
