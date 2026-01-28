import pytest
from decimal import Decimal
from datetime import datetime
from uuid import UUID
import uuid
from src.models.invoice import Invoice, InvoiceCreate, InvoiceUpdate, InvoiceStatus

def test_invoice_creation():
    """Test creating a new invoice instance"""
    invoice_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    # Generate a unique invoice number
    invoice_no = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

    invoice = Invoice(
        id=invoice_id,
        invoice_no=invoice_no,
        customer_id=customer_id,
        items='{"item1": {"product_id": "1", "quantity": 2, "price": 10.0}}',
        totals='{"subtotal": 20.0, "tax": 1.6, "total": 21.6}',
        taxes=Decimal("1.60"),
        discounts=Decimal("0.00"),
        status=InvoiceStatus.ISSUED
    )

    assert invoice.id == invoice_id
    assert invoice.invoice_no == invoice_no
    assert invoice.customer_id == customer_id
    assert invoice.items == '{"item1": {"product_id": "1", "quantity": 2, "price": 10.0}}'
    assert invoice.totals == '{"subtotal": 20.0, "tax": 1.6, "total": 21.6}'
    assert invoice.taxes == Decimal("1.60")
    assert invoice.discounts == Decimal("0.00")
    assert invoice.status == InvoiceStatus.ISSUED
    assert isinstance(invoice.created_at, datetime)
    assert isinstance(invoice.updated_at, datetime)

def test_invoice_create_schema():
    """Test InvoiceCreate schema"""
    customer_id = uuid.uuid4()

    invoice_create = InvoiceCreate(
        customer_id=customer_id,
        items='{"item1": {"product_id": "1", "quantity": 1, "price": 15.0}}',
        totals='{"subtotal": 15.0, "tax": 1.2, "total": 16.2}',
        taxes=Decimal("1.20"),
        discounts=Decimal("0.00"),
        status=InvoiceStatus.DRAFT
    )

    assert invoice_create.customer_id == customer_id
    assert invoice_create.items == '{"item1": {"product_id": "1", "quantity": 1, "price": 15.0}}'
    assert invoice_create.totals == '{"subtotal": 15.0, "tax": 1.2, "total": 16.2}'
    assert invoice_create.taxes == Decimal("1.20")
    assert invoice_create.discounts == Decimal("0.00")
    assert invoice_create.status == InvoiceStatus.DRAFT

def test_invoice_update_schema():
    """Test InvoiceUpdate schema"""
    invoice_update = InvoiceUpdate(
        status=InvoiceStatus.PAID,
        discounts=Decimal("2.00")
    )

    assert invoice_update.status == InvoiceStatus.PAID
    assert invoice_update.discounts == Decimal("2.00")

def test_invoice_statuses():
    """Test all invoice status values"""
    assert InvoiceStatus.DRAFT.value == "draft"
    assert InvoiceStatus.ISSUED.value == "issued"
    assert InvoiceStatus.PAID.value == "paid"
    assert InvoiceStatus.CANCELLED.value == "cancelled"

def test_invoice_optional_fields():
    """Test invoice with minimal required fields"""
    invoice_id = uuid.uuid4()
    customer_id = uuid.uuid4()

    # Generate a unique invoice number
    invoice_no = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

    invoice = Invoice(
        id=invoice_id,
        invoice_no=invoice_no,
        customer_id=customer_id,
        items='{}',
        totals='{"total": 0}',
    )

    assert invoice.id == invoice_id
    assert invoice.status == InvoiceStatus.DRAFT  # Default value
    assert invoice.taxes == Decimal("0.00")  # Default value
    assert invoice.discounts == Decimal("0.00")  # Default value
    assert invoice.payments == "[]"  # Default value