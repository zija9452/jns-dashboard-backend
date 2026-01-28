import pytest
from decimal import Decimal
from datetime import datetime
from uuid import UUID
import uuid
from src.models.product import Product, ProductCreate, ProductUpdate

def test_product_creation():
    """Test creating a new product instance"""
    product_id = uuid.uuid4()
    vendor_id = uuid.uuid4()

    product = Product(
        id=product_id,
        sku="PROD-001",
        name="Test Product",
        desc="A test product description",
        unit_price=Decimal("19.99"),
        cost_price=Decimal("10.00"),
        tax_rate=Decimal("0.08"),
        vendor_id=vendor_id,
        stock_level=50,
        barcode="1234567890123",
        discount=Decimal("0.05"),
        category="Electronics",
        branch="Main",
        limited_qty=False,
        brand_action="Featured"
    )

    assert product.id == product_id
    assert product.sku == "PROD-001"
    assert product.name == "Test Product"
    assert product.desc == "A test product description"
    assert product.unit_price == Decimal("19.99")
    assert product.cost_price == Decimal("10.00")
    assert product.tax_rate == Decimal("0.08")
    assert product.vendor_id == vendor_id
    assert product.stock_level == 50
    assert product.barcode == "1234567890123"
    assert product.discount == Decimal("0.05")
    assert product.category == "Electronics"
    assert product.branch == "Main"
    assert product.limited_qty is False
    assert product.brand_action == "Featured"
    assert isinstance(product.created_at, datetime)
    assert isinstance(product.updated_at, datetime)

def test_product_create_schema():
    """Test ProductCreate schema"""
    product_create = ProductCreate(
        sku="PROD-002",
        name="New Product",
        unit_price=Decimal("29.99"),
        cost_price=Decimal("15.00")
    )

    assert product_create.sku == "PROD-002"
    assert product_create.name == "New Product"
    assert product_create.unit_price == Decimal("29.99")
    assert product_create.cost_price == Decimal("15.00")
    # Test default values
    assert product_create.tax_rate == Decimal("0.00")
    assert product_create.stock_level == 0

def test_product_update_schema():
    """Test ProductUpdate schema"""
    product_update = ProductUpdate(
        name="Updated Product Name",
        stock_level=100,
        category="Updated Category"
    )

    assert product_update.name == "Updated Product Name"
    assert product_update.stock_level == 100
    assert product_update.category == "Updated Category"

def test_product_optional_fields():
    """Test product with optional fields"""
    product_id = uuid.uuid4()

    product = Product(
        id=product_id,
        sku="PROD-003",
        name="Product with Options",
        unit_price=Decimal("49.99"),
        cost_price=Decimal("25.00"),
        attributes='{"color": "red", "size": "large"}',
        branch="North"
    )

    assert product.attributes == '{"color": "red", "size": "large"}'
    assert product.branch == "North"
    assert product.desc is None
    assert product.barcode is None
    assert product.discount == Decimal("0.00")