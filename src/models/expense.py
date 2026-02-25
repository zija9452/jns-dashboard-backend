from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Numeric
from typing import Optional, Union
from decimal import Decimal
from datetime import datetime, date
import uuid

class Expense(SQLModel, table=True):
    __tablename__ = "expenses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    expense_type: str = Field(max_length=50)
    expense: str = Field(max_length=100)
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    expense_date: date = Field(default_factory=date.today)
    branch: str = Field(max_length=100, default="European Sports Light House")
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

class ExpenseRead(SQLModel):
    id: uuid.UUID
    expense_type: str
    expense: str
    amount: Decimal
    expense_date: Union[date, str]
    branch: str
    created_by: uuid.UUID
    created_at: datetime

class ExpenseCreate(SQLModel):
    expense_type: str
    expense: str
    amount: Decimal
    expense_date: date
    branch: str
    created_by: Optional[uuid.UUID] = None

class ExpenseUpdate(SQLModel):
    expense_type: Optional[str] = None
    amount: Optional[Decimal] = None
    expense_date: Optional[str] = None
    branch: Optional[str] = None