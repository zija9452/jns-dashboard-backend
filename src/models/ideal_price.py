from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal
import uuid
from sqlalchemy import Column, Numeric


class IdealPrice(SQLModel, table=True):
    __tablename__ = "ideal_prices"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(index=True)
    options_combination: str = Field(max_length=500, index=True)  # e.g., "Round Neck|Half|Polyzone 130gsm"
    min_qty: int = Field(default=1, index=True)  # Quantity tier this price applies from (1 = per-piece, 5 = bulk 5+, etc.)
    price: float = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    branch: str = Field(max_length=100, default="European Sports Light House")
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class IdealPriceCreate(SQLModel):
    category_id: uuid.UUID
    options_combination: str
    min_qty: Optional[int] = 1
    price: float
    branch: Optional[str] = "European Sports Light House"


class IdealPriceUpdate(SQLModel):
    category_id: Optional[uuid.UUID] = None
    options_combination: Optional[str] = None
    min_qty: Optional[int] = None
    price: Optional[float] = None
    branch: Optional[str] = None


class IdealPriceRead(SQLModel):
    id: uuid.UUID
    category_id: uuid.UUID
    options_combination: str
    min_qty: int
    price: float
    branch: str
    created_at: datetime
    updated_at: datetime
