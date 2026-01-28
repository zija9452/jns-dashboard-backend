import pytest
from decimal import Decimal
from datetime import datetime
from uuid import UUID
import uuid
from src.models.customer import Customer, CustomerCreate, CustomerUpdate

def test_customer_creation():
    """Test creating a new customer instance"""
    customer_id = uuid.uuid4()

    customer = Customer(
        id=customer_id,
        name="John Smith",
        contacts='{"phone": "+1234567890", "email": "john@example.com"}',
        billing_addr='{"street": "123 Main St", "city": "Anytown", "zip": "12345"}',
        shipping_addr='{"street": "123 Main St", "city": "Anytown", "zip": "12345"}',
        credit_limit=Decimal("5000.00")
    )

    assert customer.id == customer_id
    assert customer.name == "John Smith"
    assert customer.contacts == '{"phone": "+1234567890", "email": "john@example.com"}'
    assert customer.billing_addr == '{"street": "123 Main St", "city": "Anytown", "zip": "12345"}'
    assert customer.shipping_addr == '{"street": "123 Main St", "city": "Anytown", "zip": "12345"}'
    assert customer.credit_limit == Decimal("5000.00")
    assert isinstance(customer.created_at, datetime)
    assert isinstance(customer.updated_at, datetime)

def test_customer_create_schema():
    """Test CustomerCreate schema"""
    customer_create = CustomerCreate(
        name="Jane Doe",
        contacts='{"phone": "+0987654321", "email": "jane@example.com"}',
        credit_limit=Decimal("3000.00")
    )

    assert customer_create.name == "Jane Doe"
    assert customer_create.contacts == '{"phone": "+0987654321", "email": "jane@example.com"}'
    assert customer_create.credit_limit == Decimal("3000.00")
    # billing_addr and shipping_addr are optional, so they can be None

def test_customer_update_schema():
    """Test CustomerUpdate schema"""
    customer_update = CustomerUpdate(
        name="Updated Name",
        contacts='{"phone": "+1111111111", "email": "updated@example.com"}',
        credit_limit=Decimal("7000.00")
    )

    assert customer_update.name == "Updated Name"
    assert customer_update.contacts == '{"phone": "+1111111111", "email": "updated@example.com"}'
    assert customer_update.credit_limit == Decimal("7000.00")

def test_customer_optional_fields():
    """Test customer with optional fields"""
    customer_id = uuid.uuid4()

    customer = Customer(
        id=customer_id,
        name="Optional Customer",
        contacts='{"email": "optional@example.com"}',
        # billing_addr and shipping_addr are None
        credit_limit=Decimal("0.00")  # Default credit limit
    )

    assert customer.id == customer_id
    assert customer.name == "Optional Customer"
    assert customer.contacts == '{"email": "optional@example.com"}'
    assert customer.billing_addr is None
    assert customer.shipping_addr is None
    assert customer.credit_limit == Decimal("0.00")

def test_customer_with_addresses():
    """Test customer with specific billing and shipping addresses"""
    customer_id = uuid.uuid4()

    customer = Customer(
        id=customer_id,
        name="Address Test Customer",
        contacts='{"phone": "+5555555555"}',
        billing_addr='{"street": "Billing St", "city": "Billing City", "zip": "54321"}',
        shipping_addr='{"street": "Shipping Ave", "city": "Shipping Town", "zip": "98765"}',
        credit_limit=Decimal("1000.00")
    )

    assert customer.billing_addr == '{"street": "Billing St", "city": "Billing City", "zip": "54321"}'
    assert customer.shipping_addr == '{"street": "Shipping Ave", "city": "Shipping Town", "zip": "98765"}'