from sqlmodel import SQLModel, Field
from datetime import datetime
import uuid
from typing import Optional


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    branch: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CompanyCreate(SQLModel):
    name: str
    branch: Optional[str] = None


class CompanyRead(SQLModel):
    id: uuid.UUID
    name: str
    branch: Optional[str] = None
    created_at: datetime
    updated_at: datetime