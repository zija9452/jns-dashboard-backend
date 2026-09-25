from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
from enum import Enum


class ShopOrderStatus(str, Enum):
    PENDING = "PENDING"
    IN_PRODUCTION = "IN_PRODUCTION"
    DELIVERED = "DELIVERED"
    CANCEL = "CANCEL"


class ShopOrderApprovalStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ShopOrder(SQLModel, table=True):
    __tablename__ = "shop_orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True)
    product_name: str = Field(max_length=100)  # Snapshot at order time
    barcode: Optional[str] = Field(default=None, max_length=50)  # Snapshot at order time
    category: Optional[str] = Field(default=None, max_length=50)  # Snapshot at order time
    stock_at_order_time: int = Field(default=0)
    quantity_ordered: int
    note: Optional[str] = Field(default=None, max_length=255)
    status: ShopOrderStatus = Field(default=ShopOrderStatus.PENDING, index=True)
    in_production_at: Optional[datetime] = Field(default=None)  # Set when status moves to IN_PRODUCTION
    delivered_at: Optional[datetime] = Field(default=None)  # Set when status moves to DELIVERED
    cancelled_at: Optional[datetime] = Field(default=None)  # Set when status moves to CANCEL
    approval_status: ShopOrderApprovalStatus = Field(default=ShopOrderApprovalStatus.PENDING_APPROVAL, index=True)
    approved_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    approved_at: Optional[datetime] = Field(default=None)
    rejected_at: Optional[datetime] = Field(default=None)
    seen_by_admin: bool = Field(default=False, index=True)  # Cleared once admin opens the approval list
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)


class ShopOrderSeenByUser(SQLModel, table=True):
    """Tracks which approved orders each individual user has already seen on
    the Shop Orders page, so one user opening the page doesn't clear the
    "new order" badge for every other user (accounts are unique, so this is
    tracked per user rather than per role - two admins don't share a badge)."""
    __tablename__ = "shop_order_seen_by_user"

    order_id: uuid.UUID = Field(foreign_key="shop_orders.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)


class ShopOrderApprovalSeenByUser(SQLModel, table=True):
    """Tracks which pending-approval orders each individual user has already
    seen on the Shop Order Approval page, so one admin/production user
    opening the page doesn't clear the badge for every other admin/production
    user."""
    __tablename__ = "shop_order_approval_seen_by_user"

    order_id: uuid.UUID = Field(foreign_key="shop_orders.id", primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)


class ShopOrderRead(SQLModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    barcode: Optional[str]
    category: Optional[str]
    stock_at_order_time: int
    quantity_ordered: int
    note: Optional[str]
    status: ShopOrderStatus
    in_production_at: Optional[datetime]
    delivered_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    approval_status: ShopOrderApprovalStatus
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ShopOrderCreate(SQLModel):
    product_id: uuid.UUID
    quantity_ordered: int
    note: Optional[str] = Field(default=None, max_length=255)


class ShopOrderUpdate(SQLModel):
    status: Optional[ShopOrderStatus] = None


class ShopOrderReview(SQLModel):
    action: str  # "approve" or "reject"
