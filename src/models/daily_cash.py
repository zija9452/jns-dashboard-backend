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

    # Cash
    cash_opening: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    cash_closing: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    cash_sales: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))

    # EasyPaisa Zohaib
    easypaisa_zohaib_opening: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    easypaisa_zohaib_closing: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    easypaisa_zohaib_sales: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))

    # EasyPaisa Yasir
    easypaisa_yasir_opening: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    easypaisa_yasir_closing: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    easypaisa_yasir_sales: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))

    # Bank
    bank_opening: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    bank_closing: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    bank_sales: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))

    # Total (all payment methods combined)
    total_opening: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    total_sales: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))
    total_expected: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    total_closing: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))
    total_difference: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2)))

    # Notes
    opening_notes: Optional[str] = Field(default=None)
    closing_notes: Optional[str] = Field(default=None)
    created_at: Optional[date_type] = Field(default=None)
    updated_at: Optional[date_type] = Field(default=None)


class DailyCashCreate(SQLModel):
    date: date_type
    cash_opening: Optional[Decimal] = 0.00
    cash_sales: Optional[Decimal] = 0.00
    easypaisa_zohaib_opening: Optional[Decimal] = 0.00
    easypaisa_zohaib_sales: Optional[Decimal] = 0.00
    easypaisa_yasir_opening: Optional[Decimal] = 0.00
    easypaisa_yasir_sales: Optional[Decimal] = 0.00
    bank_opening: Optional[Decimal] = 0.00
    bank_sales: Optional[Decimal] = 0.00
    total_opening: Optional[Decimal] = 0.00
    total_sales: Optional[Decimal] = 0.00
    opening_notes: Optional[str] = None
    closing_notes: Optional[str] = None


class DailyCashUpdate(SQLModel):
    cash_closing: Optional[Decimal] = None
    easypaisa_zohaib_closing: Optional[Decimal] = None
    easypaisa_yasir_closing: Optional[Decimal] = None
    bank_closing: Optional[Decimal] = None
    total_closing: Optional[Decimal] = None
    total_expected: Optional[Decimal] = None
    total_difference: Optional[Decimal] = None
    closing_notes: Optional[str] = None


class DailyCashRead(SQLModel):
    id: uuid.UUID
    date: date_type
    cash_opening: Decimal
    cash_sales: Decimal
    easypaisa_zohaib_opening: Decimal
    easypaisa_zohaib_sales: Decimal
    easypaisa_yasir_opening: Decimal
    easypaisa_yasir_sales: Decimal
    bank_opening: Decimal
    bank_sales: Decimal
    total_opening: Decimal
    total_sales: Decimal
    total_expected: Optional[Decimal]
    total_closing: Optional[Decimal]
    total_difference: Optional[Decimal]
    opening_notes: Optional[str]
    closing_notes: Optional[str]
    created_at: Optional[date_type]
    updated_at: Optional[date_type]
