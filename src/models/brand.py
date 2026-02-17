from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Brand(SQLModel, table=True):
    __tablename__ = "brands"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class BrandCreate(SQLModel):
    name: str


class BrandUpdate(SQLModel):
    name: Optional[str] = None


class BrandRead(SQLModel):
    id: uuid.UUID
    name: str
    created_at: datetime
