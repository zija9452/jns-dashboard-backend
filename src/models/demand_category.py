from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class DemandCategory(SQLModel, table=True):
    __tablename__ = "demand_categories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, max_length=100)
    sort_order: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class DemandCategoryCreate(SQLModel):
    name: str
    sort_order: Optional[int] = None


class DemandCategoryUpdate(SQLModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


class DemandCategoryRead(SQLModel):
    id: uuid.UUID
    name: str
    sort_order: int
    created_at: datetime
