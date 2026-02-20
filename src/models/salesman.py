from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid

class Salesman(SQLModel, table=True):
    __tablename__ = "salesmen"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=200)
    branch: Optional[str] = Field(default=None, max_length=50)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

class SalesmanRead(SQLModel):
    id: uuid.UUID
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    branch: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class SalesmanCreate(SQLModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    branch: Optional[str] = None

class SalesmanUpdate(SQLModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    branch: Optional[str] = None