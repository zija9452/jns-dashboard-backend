from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid


class RushPricingSetting(SQLModel, table=True):
    """
    Rush-order rule: an order is automatically rush when the customer's required-by
    date is within `threshold_days` of today. When rush, the fixed per-piece surcharge
    applies across the whole order (rate x total pieces). Not a manual toggle - derived
    from the deadline. One row per branch.
    """
    __tablename__ = "rush_pricing_settings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    price_per_piece: Decimal = Field(default=300.00, sa_column=Column(Numeric(10, 2), nullable=False))
    threshold_days: int = Field(default=4)  # required-by date within this many days of today => rush
    branch: str = Field(max_length=100, default="European Sports Light House", unique=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class RushPricingSettingUpdate(SQLModel):
    price_per_piece: Decimal
    threshold_days: int


class RushPricingSettingRead(SQLModel):
    id: uuid.UUID
    price_per_piece: Decimal
    threshold_days: int
    branch: str
    updated_at: datetime
