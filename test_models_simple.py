"""
Test to verify that the models in the current codebase work properly
without causing Pydantic v2 recursion errors.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal

# Import only the specific model classes we need to test
from src.models.user import User, UserRead, UserCreate, UserUpdate
from src.models.role import Role, RoleRead, RoleCreate, RoleUpdate
from src.models.invoice import Invoice, InvoiceRead, InvoiceCreate, InvoiceUpdate
from src.models.refund import Refund, RefundRead, RefundCreate, RefundUpdate
from src.models.salesman import Salesman, SalesmanRead, SalesmanCreate, SalesmanUpdate
from src.models.expense import Expense, ExpenseRead, ExpenseCreate, ExpenseUpdate


def test_basic_model_creation():
    """Test that basic model creation works without recursion errors."""
    print("Testing basic model creation...")

    # Test user models
    user_create = UserCreate(
        full_name="John Doe",
        email="john@example.com",
        username="johndoe",
        role_id=uuid.uuid4(),
        password="securepassword"
    )
    print(f"OK UserCreate: {str(user_create)[:100]}...")  # Truncate for safety

    user_read = UserRead(
        id=uuid.uuid4(),
        full_name="John Doe",
        email="john@example.com",
        username="johndoe",
        role_id=uuid.uuid4(),
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"OK UserRead: {str(user_read)[:100]}...")

    # Test role models
    role_create = RoleCreate(
        name="admin",
        permissions='{"read": true, "write": true}'
    )
    print(f"OK RoleCreate: {str(role_create)[:100]}...")

    role_read = RoleRead(
        id=uuid.uuid4(),
        name="admin",
        permissions='{"read": true, "write": true}'
    )
    print(f"OK RoleRead: {str(role_read)[:100]}...")

    # Test invoice models
    invoice_create = InvoiceCreate(
        customer_id=uuid.uuid4(),
        items='{"item1": "value1"}',
        totals='{"subtotal": 100, "tax": 10, "total": 110}'
    )
    print(f"OK InvoiceCreate: {str(invoice_create)[:100]}...")

    # Test refund models
    refund_create = RefundCreate(
        invoice_id=uuid.uuid4(),
        items='{"item1": "value1"}',
        amount=50.00,
        reason="Wrong item",
        processed_by=uuid.uuid4()
    )
    print(f"OK RefundCreate: {str(refund_create)[:100]}...")

    # Test salesman models
    salesman_create = SalesmanCreate(
        name="Jane Smith",
        code="JS001",
        commission_rate=0.05
    )
    print(f"OK SalesmanCreate: {str(salesman_create)[:100]}...")

    # Test expense models
    expense_create = ExpenseCreate(
        expense_type="Office Supplies",
        amount=Decimal('45.99'),
        note="Pens and paper",
        created_by=uuid.uuid4()
    )
    print(f"OK ExpenseCreate: {str(expense_create)[:100]}...")

    print("\nOK All basic model creations succeeded!")


def test_model_instances():
    """Test creating full model instances."""
    print("\nTesting model instances...")

    # Create role
    role = Role(
        id=uuid.uuid4(),
        name="admin",
        permissions='{"read": true, "write": true}',
        created_at=datetime.now()
    )
    print(f"OK Created role instance")

    # Create user
    user = User(
        id=uuid.uuid4(),
        full_name="John Doe",
        email="john@example.com",
        username="johndoe",
        role_id=role.id,
        password_hash="hashed_password",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"OK Created user instance")

    # Create invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        invoice_no="INV-001",
        customer_id=uuid.uuid4(),
        items='{"product1": {"quantity": 2, "price": 25.00}, "product2": {"quantity": 1, "price": 50.00}}',
        totals='{"subtotal": 100.00, "tax": 10.00, "total": 110.00}',
        taxes=Decimal('10.00'),
        discounts=Decimal('5.00'),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"OK Created invoice instance")

    # Create refund
    refund = Refund(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        items='{"product1": {"quantity": 1, "amount": 25.00}}',
        amount=Decimal('25.00'),
        reason="Customer return",
        processed_by=uuid.uuid4(),
        created_at=datetime.now()
    )
    print(f"OK Created refund instance")

    # Create salesman
    salesman = Salesman(
        id=uuid.uuid4(),
        name="Jane Smith",
        code="JS001",
        commission_rate=Decimal('0.05'),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"OK Created salesman instance")

    # Create expense
    expense = Expense(
        id=uuid.uuid4(),
        expense_type="Office Supplies",
        amount=Decimal('45.99'),
        expense_date=date.today(),
        note="Pens and paper",
        created_by=uuid.uuid4(),
        created_at=datetime.now()
    )
    print(f"OK Created expense instance")

    print("\nOK All model instances created successfully!")


if __name__ == "__main__":
    print("Testing Pydantic v2 models in the codebase...")
    print("=" * 50)

    try:
        test_basic_model_creation()
        test_model_instances()

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! No recursion errors detected.")
        print("The models in the codebase are safe from Pydantic v2 recursion issues.")

    except RecursionError as e:
        print(f"\nERROR RECURSION DETECTED: {e}")
        print("There is still a recursion issue that needs to be addressed.")

    except Exception as e:
        print(f"\nERROR OTHER ERROR: {e}")
        import traceback
        traceback.print_exc()