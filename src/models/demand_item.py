from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class DemandItem(SQLModel, table=True):
    __tablename__ = "demand_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, max_length=150, index=True)
    category: Optional[str] = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class DemandItemCreate(SQLModel):
    name: str
    category: Optional[str] = None


class DemandItemUpdate(SQLModel):
    name: Optional[str] = None
    category: Optional[str] = None


class DemandItemRead(SQLModel):
    id: uuid.UUID
    name: str
    category: Optional[str]
    created_at: datetime
