from sqlmodel import SQLModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB


class SubCategorySchema(SQLModel):
    """Schema for a sub-category with its options"""
    sub_category: str
    options: List[str]
    # True = a price adjustment dimension (Sleeves, Size Type...) applied on top of
    # the base ideal_price, not a separate priced combination - see price_modifiers.
    is_modifier: bool = False
    # True = hidden by default in the item-entry form (Quotation / Customer Invoice),
    # revealed only via the "+" more-options toggle - for dimensions that don't apply
    # to every order (e.g. Rib, Zip).
    is_optional: bool = False


class CustomerCategory(SQLModel, table=True):
    """
    Customer Category Model - Single Row Per Main Category
    -------------------------------------------------------
    Structure: One row per main category with JSONB array of sub-categories
    
    Example:
    {
      "id": "uuid",
      "main_category": "T-Shirt",
      "sub_categories": [
        {
          "sub_category": "Neck",
          "options": ["Round", "V-Neck", "Sherwani", "Polo"]
        },
        {
          "sub_category": "Fabric",
          "options": ["Polyzone", "Mesh", "Other"]
        }
      ],
      "branch": "European Sports Light House",
      "created_at": "2026-04-01T00:00:00"
    }
    """
    __tablename__ = "customer_categories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    main_category: str = Field(max_length=100, unique=True, index=True)
    sub_categories: List[Dict[str, Any]] = Field(
        default=[],
        sa_column=Column(JSONB, nullable=False, default=list)
    )
    branch: str = Field(max_length=100, default="European Sports Light House")
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class CustomerCategoryCreate(SQLModel):
    main_category: str
    sub_categories: List[SubCategorySchema]
    branch: Optional[str] = "European Sports Light House"


class CustomerCategoryUpdate(SQLModel):
    main_category: Optional[str] = None
    sub_categories: Optional[List[SubCategorySchema]] = None
    branch: Optional[str] = None


class CustomerCategoryRead(SQLModel):
    id: uuid.UUID
    main_category: str
    sub_categories: List[Dict[str, Any]]
    branch: str
    created_at: datetime


class SubCategoryGroup(SQLModel):
    """For grouped response"""
    sub_category: str
    options: List[str]
    is_modifier: bool = False
    is_optional: bool = False


class CustomerCategoryGrouped(SQLModel):
    """Grouped response for frontend"""
    main_category: str
    sub_categories: List[SubCategoryGroup]
