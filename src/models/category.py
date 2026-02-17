from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, max_length=100)
    branch: str = Field(max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class CategoryCreate(SQLModel):
    name: str
    branch: str


class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    branch: Optional[str] = None


class CategoryRead(SQLModel):
    id: uuid.UUID
    name: str
    branch: str
    created_at: datetime
