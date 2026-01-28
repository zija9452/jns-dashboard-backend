from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid
import json

class Vendor(SQLModel, table=True):
    __tablename__ = "vendors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    contacts: str = Field()  # JSON string for phone, email, address
    terms: Optional[str] = Field(default=None)  # JSON string for payment terms, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

class VendorRead(SQLModel):
    id: uuid.UUID
    name: str
    contacts: str
    terms: Optional[str]
    created_at: datetime
    updated_at: datetime

class VendorCreate(SQLModel):
    name: str
    contacts: str  # JSON string
    terms: Optional[str] = None  # JSON string

class VendorUpdate(SQLModel):
    name: Optional[str] = None
    contacts: Optional[str] = None
    terms: Optional[str] = None