from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
from enum import Enum


class ShopOrderStatus(str, Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    CANCEL = "CANCEL"


class ShopOrder(SQLModel, table=True):
    __tablename__ = "shop_orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True)
    product_name: str = Field(max_length=100)  # Snapshot at order time
    barcode: Optional[str] = Field(default=None, max_length=50)  # Snapshot at order time
    category: Optional[str] = Field(default=None, max_length=50)  # Snapshot at order time
    stock_at_order_time: int = Field(default=0)
    quantity_ordered: int
    status: ShopOrderStatus = Field(default=ShopOrderStatus.PENDING, index=True)
    delivered_at: Optional[datetime] = Field(default=None)  # Set when status moves to DELIVERED
    cancelled_at: Optional[datetime] = Field(default=None)  # Set when status moves to CANCEL
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)


class ShopOrderRead(SQLModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    barcode: Optional[str]
    category: Optional[str]
    stock_at_order_time: int
    quantity_ordered: int
    status: ShopOrderStatus
    delivered_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ShopOrderCreate(SQLModel):
    product_id: uuid.UUID
    quantity_ordered: int


class ShopOrderUpdate(SQLModel):
    status: Optional[ShopOrderStatus] = None
