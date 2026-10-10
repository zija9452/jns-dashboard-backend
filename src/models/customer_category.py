from sqlmodel import SQLModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from decimal import Decimal
from sqlalchemy import Column, Numeric, Boolean, String, text
from sqlalchemy.dialects.postgresql import JSONB
from ..config.branches import current_branch_name


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
    # Options of this sub-category ticked "Dye" (e.g. ["Dye Fabric"]). A line with a dye
    # option gets no flat charge; its rate is raised by the category's dye rates instead.
    dye_options: List[str] = []


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
    branch: str = Field(max_length=100, default_factory=current_branch_name)
    # This category's own designing / mockup charge (added once when the category has
    # only 1-4 pcs in an order), set on the Ideal Pricing page. None or 0 = no mockup charge.
    mockup_charge: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    # True = Quotation / Customer Invoice show the optional DTF logos box (width x height
    # per logo, priced by roll length - see dtf_pricing_settings) for this category.
    # Ticked on the Customer Category page; Hoodie and Jacket for now.
    dtf_enabled: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default=text("false")))
    # Dye lines' rate multiplier, by the category's dye pieces: 1-4 pcs and 5-15 pcs
    # (16+ = normal rate). Set on the Ideal Pricing page.
    dye_rate_single: Decimal = Field(default=Decimal("2"), sa_column=Column(Numeric(5, 2), nullable=False, server_default=text("2")))
    dye_rate_qty: Decimal = Field(default=Decimal("1.5"), sa_column=Column(Numeric(5, 2), nullable=False, server_default=text("1.5")))
    # Kit (Quotation / Customer Invoice): what this category is in a team's kit -
    # "jersey", "short", "trouser" or None. For a team that is one of our ready articles
    # (products page), the first Jersey / Short added pays kit_flat_charge instead of the
    # flat charge and the other pays 0; a Trouser pays 0 when the team's Jersey is in the
    # order. Set on the Customer Category page.
    kit_role: Optional[str] = Field(default=None, sa_column=Column(String(10), nullable=True))
    kit_flat_charge: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(10, 2), nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class CustomerCategoryCreate(SQLModel):
    main_category: str
    sub_categories: List[SubCategorySchema]
    branch: Optional[str] = Field(default_factory=current_branch_name)
    mockup_charge: Optional[Decimal] = None
    dtf_enabled: bool = False
    dye_rate_single: Decimal = Decimal("2")
    dye_rate_qty: Decimal = Decimal("1.5")
    kit_role: Optional[str] = None
    kit_flat_charge: Optional[Decimal] = None


class CustomerCategoryUpdate(SQLModel):
    main_category: Optional[str] = None
    sub_categories: Optional[List[SubCategorySchema]] = None
    branch: Optional[str] = None
    mockup_charge: Optional[Decimal] = None  # send null for no mockup charge
    dtf_enabled: Optional[bool] = None
    dye_rate_single: Optional[Decimal] = None  # null = leave as is
    dye_rate_qty: Optional[Decimal] = None
    kit_role: Optional[str] = None  # send null (or "") for not part of a kit
    kit_flat_charge: Optional[Decimal] = None


class CustomerCategoryRead(SQLModel):
    id: uuid.UUID
    main_category: str
    sub_categories: List[Dict[str, Any]]
    branch: str
    mockup_charge: Optional[Decimal] = None
    dtf_enabled: bool = False
    dye_rate_single: Decimal = Decimal("2")
    dye_rate_qty: Decimal = Decimal("1.5")
    kit_role: Optional[str] = None
    kit_flat_charge: Optional[Decimal] = None
    created_at: datetime


class SubCategoryGroup(SQLModel):
    """For grouped response"""
    sub_category: str
    options: List[str]
    is_modifier: bool = False
    is_optional: bool = False
    dye_options: List[str] = []


class CustomerCategoryGrouped(SQLModel):
    """Grouped response for frontend"""
    main_category: str
    sub_categories: List[SubCategoryGroup]
