from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric, Date
from typing import Optional
from decimal import Decimal
from datetime import date as date_type
import uuid


class DailyCash(SQLModel, table=True):
    __tablename__ = "daily_cash"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    date: date_type = Field(sa_column=Column(Date, unique=True, index=True))  # One record per day

    # Cash only (simplified)
    cash_opening: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    cash_closing: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    cash_sales: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    cash_expected: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    cash_difference: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))

    # Notes
    opening_notes: Optional[str] = Field(default=None)
    closing_notes: Optional[str] = Field(default=None)
    created_at: Optional[date_type] = Field(default=None)
    updated_at: Optional[date_type] = Field(default=None)


class DailyCashCreate(SQLModel):
    date: date_type
    cash_opening: Optional[Decimal] = 0.00
    cash_closing: Optional[Decimal] = None
    cash_sales: Optional[Decimal] = 0.00
    cash_expected: Optional[Decimal] = None
    cash_difference: Optional[Decimal] = None
    opening_notes: Optional[str] = None
    closing_notes: Optional[str] = None


class DailyCashUpdate(SQLModel):
    cash_opening: Optional[Decimal] = None
    cash_closing: Optional[Decimal] = None
    cash_sales: Optional[Decimal] = None
    cash_expected: Optional[Decimal] = None
    cash_difference: Optional[Decimal] = None
    opening_notes: Optional[str] = None
    closing_notes: Optional[str] = None


class DailyCashRead(SQLModel):
    id: uuid.UUID
    date: date_type
    cash_opening: Decimal
    cash_closing: Optional[Decimal]
    cash_sales: Decimal
    cash_expected: Optional[Decimal]
    cash_difference: Optional[Decimal]
    opening_notes: Optional[str]
    closing_notes: Optional[str]
    created_at: Optional[date_type]
    updated_at: Optional[date_type]
