from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
from enum import Enum


class DemandStatus(str, Enum):
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class Demand(SQLModel, table=True):
    __tablename__ = "demands"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    demand_text: str = Field(max_length=255)
    category: Optional[str] = Field(default=None, max_length=50)
    customer_name: Optional[str] = Field(default=None, max_length=100)
    customer_phone: Optional[str] = Field(default=None, max_length=20)
    status: DemandStatus = Field(default=DemandStatus.PENDING, index=True)
    fulfilled_at: Optional[datetime] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, index=True)


class DemandRead(SQLModel):
    id: uuid.UUID
    demand_text: str
    category: Optional[str]
    customer_name: Optional[str]
    customer_phone: Optional[str]
    status: DemandStatus
    fulfilled_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DemandCreate(SQLModel):
    demand_text: str
    category: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None


class DemandUpdate(SQLModel):
    demand_text: Optional[str] = None
    category: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    status: Optional[DemandStatus] = None
