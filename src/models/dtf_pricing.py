from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric
from decimal import Decimal
from datetime import datetime
import uuid
from ..config.branches import current_branch_name


class DtfPricingSetting(SQLModel, table=True):
    """
    DTF logo printing rule for Hoodie / Jacket lines (categories with
    customer_categories.dtf_enabled). The logos are laid out on a roll `roll_width_in`
    wide with `gap_in` between them; the roll length used is charged in steps of
    0.5 m, `price_per_half_meter` per step (0.5 m = 750, 1 m = 1500...). One row per branch.
    """
    __tablename__ = "dtf_pricing_settings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    price_per_half_meter: Decimal = Field(default=750.00, sa_column=Column(Numeric(10, 2), nullable=False))
    roll_width_in: Decimal = Field(default=23.00, sa_column=Column(Numeric(6, 2), nullable=False))
    gap_in: Decimal = Field(default=0.50, sa_column=Column(Numeric(6, 2), nullable=False))
    branch: str = Field(max_length=100, default_factory=current_branch_name, unique=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class DtfPricingSettingUpdate(SQLModel):
    price_per_half_meter: Decimal
    roll_width_in: Decimal
    gap_in: Decimal


class DtfPricingSettingRead(SQLModel):
    id: uuid.UUID
    price_per_half_meter: Decimal
    roll_width_in: Decimal
    gap_in: Decimal
    branch: str
    updated_at: datetime
