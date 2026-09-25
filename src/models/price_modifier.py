from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Numeric, Enum as SAEnum
from typing import Optional
from decimal import Decimal
from datetime import datetime
import uuid
from enum import Enum


class AdjustmentType(str, Enum):
    FLAT = "flat"          # add/subtract a fixed rupee amount
    MULTIPLY = "multiply"  # multiply the running price by this factor (e.g. 2.0 = double)


class PriceModifier(SQLModel, table=True):
    """
    A price adjustment for one option of a "modifier" sub-category (e.g. Sleeves:
    Full = +50, Size Type: Oversize+ = x2), applied on top of the base ideal_price
    instead of needing a separate fixed price for every combination.
    """
    __tablename__ = "price_modifiers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(index=True)
    sub_category: str = Field(max_length=100, index=True)
    option_value: str = Field(max_length=100)
    # values_callable: store/read the lowercase VALUE ("flat"/"multiply") rather than
    # SQLAlchemy's default of the uppercase member NAME - the column is a plain
    # VARCHAR holding "flat"/"multiply" (matches the frontend's TS union), not a
    # Postgres-level enum type. native_enum=False is required too - without it
    # SQLAlchemy still emits an explicit "::adjustmenttype" cast on every bound
    # parameter assuming a native PG enum type exists, which breaks inserts the
    # moment such a type happens to exist in the DB with different labels than
    # what values_callable produces (seen as: "invalid input value for enum
    # adjustmenttype").
    adjustment_type: AdjustmentType = Field(
        default=AdjustmentType.FLAT,
        sa_column=Column(
            SAEnum(AdjustmentType, values_callable=lambda enum_cls: [e.value for e in enum_cls], native_enum=False, length=20),
            nullable=False
        )
    )
    value: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())


class PriceModifierCreate(SQLModel):
    category_id: uuid.UUID
    sub_category: str
    option_value: str
    adjustment_type: AdjustmentType = AdjustmentType.FLAT
    value: Decimal


class PriceModifierUpdate(SQLModel):
    adjustment_type: Optional[AdjustmentType] = None
    value: Optional[Decimal] = None


class PriceModifierRead(SQLModel):
    id: uuid.UUID
    category_id: uuid.UUID
    sub_category: str
    option_value: str
    adjustment_type: AdjustmentType
    value: Decimal
    created_at: datetime
    updated_at: datetime
