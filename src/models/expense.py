from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from decimal import Decimal
from datetime import datetime, date
import uuid

class Expense(SQLModel, table=True):
    __tablename__ = "expenses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    expense_type: str = Field(max_length=50)  # e.g., rent, utilities, supplies
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    date: date = Field(default_factory=date.today)
    note: Optional[str] = Field(default=None)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

class ExpenseRead(SQLModel):
    id: uuid.UUID
    expense_type: str
    amount: Decimal
    date: date
    note: Optional[str]
    created_by: uuid.UUID
    created_at: datetime

class ExpenseCreate(SQLModel):
    expense_type: str
    amount: Decimal
    date: Optional[date] = None
    note: Optional[str] = None
    created_by: uuid.UUID

class ExpenseUpdate(SQLModel):
    type: Optional[str] = None
    amount: Optional[Decimal] = None
    date: Optional[date] = None
    note: Optional[str] = None