from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid
import json
from enum import Enum

class CustomOrderStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CustomOrder(SQLModel, table=True):
    __tablename__ = "custom_orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fields: str = Field()  # JSON string for custom order data
    status: CustomOrderStatus = Field(default=CustomOrderStatus.PENDING)
    linked_invoice: Optional[uuid.UUID] = Field(default=None, foreign_key="invoices.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

class CustomOrderRead(SQLModel):
    id: uuid.UUID
    fields: str
    status: CustomOrderStatus
    linked_invoice: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

class CustomOrderCreate(SQLModel):
    fields: str  # JSON string
    status: Optional[CustomOrderStatus] = CustomOrderStatus.PENDING
    linked_invoice: Optional[uuid.UUID] = None

class CustomOrderUpdate(SQLModel):
    fields: Optional[str] = None
    status: Optional[CustomOrderStatus] = None
    linked_invoice: Optional[uuid.UUID] = None