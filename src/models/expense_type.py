from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ExpenseType(SQLModel, table=True):
    __tablename__ = "expense_types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class ExpenseTypeCreate(SQLModel):
    name: str


class ExpenseTypeUpdate(SQLModel):
    name: Optional[str] = None


class ExpenseTypeRead(SQLModel):
    id: uuid.UUID
    name: str
    created_at: datetime
