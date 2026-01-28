import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session
from uuid import UUID
import uuid
from decimal import Decimal
from datetime import datetime

from src.services.product_service import ProductService
from src.models.product import Product, ProductCreate, ProductUpdate

@pytest.mark.asyncio
async def test_create_product():
    """Test creating a product"""
    # Mock the database session
    mock_db = MagicMock(spec=Session)

    # Sample product creation data
    product_create_data = ProductCreate(
        sku="TEST-001",
        name="Test Product",
        desc="A test product",
        unit_price=Decimal("19.99"),
        cost_price=Decimal("10.00"),
        tax_rate=Decimal("0.08"),
        stock_level=50,
        barcode="1234567890123",
        category="Electronics",
        branch="Main"
    )

    # Create a mock product object to return
    created_product = Product(
        id=uuid.uuid4(),
        sku=product_create_data.sku,
        name=product_create_data.name,
        desc=product_create_data.desc,
        unit_price=product_create_data.unit_price,
        cost_price=product_create_data.cost_price,
        tax_rate=product_create_data.tax_rate,
        stock_level=product_create_data.stock_level,
        barcode=product_create_data.barcode,
        category=product_create_data.category,
        branch=product_create_data.branch
    )

    # Mock the database operations
    with patch.object(mock_db, 'add') as mock_add:
        with patch.object(mock_db, 'commit') as mock_commit:
            with patch.object(mock_db, 'refresh', return_value=None):
                # Call the service method
                result = await ProductService.create_product(mock_db, product_create_data)

                # Assertions
                assert result.sku == product_create_data.sku
                assert result.name == product_create_data.name
                assert result.unit_price == product_create_data.unit_price
                assert result.stock_level == product_create_data.stock_level

                # Verify database operations were called
                mock_add.assert_called_once()
                mock_commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_product():
    """Test getting a product by ID"""
    mock_db = MagicMock(spec=Session)
    product_id = uuid.uuid4()

    # Create a mock product
    mock_product = Product(
        id=product_id,
        sku="TEST-002",
        name="Another Test Product",
        unit_price=Decimal("29.99"),
        cost_price=Decimal("15.00"),
        stock_level=25
    )

    # Mock the database query
    mock_exec = MagicMock()
    mock_exec.first.return_value = mock_product

    with patch.object(mock_db, 'exec', return_value=mock_exec):
        result = await ProductService.get_product(mock_db, product_id)

        assert result.id == product_id
        assert result.sku == "TEST-002"
        assert result.name == "Another Test Product"

        # Verify the query was constructed properly
        mock_exec.first.assert_called_once()

@pytest.mark.asyncio
async def test_get_product_by_sku():
    """Test getting a product by SKU"""
    mock_db = MagicMock(spec=Session)
    sku = "TEST-003"

    # Create a mock product
    mock_product = Product(
        id=uuid.uuid4(),
        sku=sku,
        name="SKU Test Product",
        unit_price=Decimal("39.99"),
        cost_price=Decimal("20.00"),
        stock_level=10
    )

    # Mock the database query
    mock_exec = MagicMock()
    mock_exec.first.return_value = mock_product

    with patch.object(mock_db, 'exec', return_value=mock_exec):
        result = await ProductService.get_product_by_sku(mock_db, sku)

        assert result.sku == sku
        assert result.name == "SKU Test Product"

@pytest.mark.asyncio
async def test_update_product():
    """Test updating a product"""
    mock_db = MagicMock(spec=Session)
    product_id = uuid.uuid4()

    # Create a mock existing product
    existing_product = Product(
        id=product_id,
        sku="OLD-001",
        name="Old Product Name",
        unit_price=Decimal("9.99"),
        cost_price=Decimal("5.00"),
        stock_level=5,
        category="Old Category"
    )

    # Create update data
    product_update = ProductUpdate(
        name="New Product Name",
        unit_price=Decimal("14.99"),
        stock_level=15,
        category="New Category"
    )

    # Mock the get_product method to return the existing product
    with patch('src.services.product_service.ProductService.get_product', return_value=existing_product):
        with patch('src.services.product_service.audit_log') as mock_audit:
            with patch.object(mock_db, 'commit') as mock_commit:
                with patch.object(mock_db, 'refresh') as mock_refresh:
                    result = await ProductService.update_product(mock_db, product_id, product_update)

                    # Verify the updates were applied
                    assert result.name == "New Product Name"
                    assert result.unit_price == Decimal("14.99")
                    assert result.stock_level == 15
                    assert result.category == "New Category"
                    # SKU should remain unchanged
                    assert result.sku == "OLD-001"

                    # Verify database operations
                    mock_commit.assert_called_once()
                    mock_refresh.assert_called_once()
                    # Audit log should be called
                    mock_audit.assert_called()

@pytest.mark.asyncio
async def test_delete_product():
    """Test deleting a product"""
    mock_db = MagicMock(spec=Session)
    product_id = uuid.uuid4()

    # Create a mock product to delete
    mock_product = Product(
        id=product_id,
        sku="DEL-001",
        name="To Be Deleted Product",
        unit_price=Decimal("1.99"),
        cost_price=Decimal("0.99"),
        stock_level=1
    )

    # Mock the get_product method to return the product
    with patch('src.services.product_service.ProductService.get_product', return_value=mock_product):
        with patch('src.services.product_service.audit_log') as mock_audit:
            with patch.object(mock_db, 'delete') as mock_delete:
                with patch.object(mock_db, 'commit') as mock_commit:
                    result = await ProductService.delete_product(mock_db, product_id)

                    # Verify the product was found and deletion was attempted
                    assert result is True

                    # Verify database operations
                    mock_delete.assert_called_once_with(mock_product)
                    mock_commit.assert_called_once()
                    # Audit log should be called
                    mock_audit.assert_called()

@pytest.mark.asyncio
async def test_delete_nonexistent_product():
    """Test deleting a product that doesn't exist"""
    mock_db = MagicMock(spec=Session)
    product_id = uuid.uuid4()

    # Mock the get_product method to return None (product not found)
    with patch('src.services.product_service.ProductService.get_product', return_value=None):
        result = await ProductService.delete_product(mock_db, product_id)

        # Verify the product was not found
        assert result is False

@pytest.mark.asyncio
async def test_adjust_stock():
    """Test adjusting product stock"""
    mock_db = MagicMock(spec=Session)
    product_id = uuid.uuid4()

    # Create a mock product
    existing_product = Product(
        id=product_id,
        sku="STOCK-001",
        name="Stock Test Product",
        unit_price=Decimal("19.99"),
        cost_price=Decimal("10.00"),
        stock_level=50  # Starting stock
    )

    # Mock the get_product method
    with patch('src.services.product_service.ProductService.get_product', return_value=existing_product):
        with patch('src.services.product_service.audit_log') as mock_audit:
            with patch.object(mock_db, 'commit') as mock_commit:
                with patch.object(mock_db, 'refresh') as mock_refresh:
                    # Test increasing stock by 10
                    result = await ProductService.adjust_stock(mock_db, product_id, 10)

                    # Verify stock was increased
                    assert result.stock_level == 60  # 50 + 10

                    # Test decreasing stock by 5
                    result = await ProductService.adjust_stock(mock_db, product_id, -5)

                    # Verify stock was decreased
                    assert result.stock_level == 55  # 60 - 5

                    # Verify database operations
                    assert mock_commit.call_count == 2
                    assert mock_refresh.call_count == 2
                    # Audit log should be called twice
                    assert mock_audit.call_count == 2