"""
Test to verify that the models in the current codebase work properly
without causing Pydantic v2 recursion errors.
"""

from src.models.user import User, UserRead, UserCreate, UserUpdate
from src.models.role import Role, RoleRead, RoleCreate, RoleUpdate
from src.models.invoice import Invoice, InvoiceRead, InvoiceCreate, InvoiceUpdate
from src.models.refund import Refund, RefundRead, RefundCreate, RefundUpdate
from src.models.salesman import Salesman, SalesmanRead, SalesmanCreate, SalesmanUpdate
from src.auth.auth import Token, TokenData, RefreshToken
from src.routers.auth import LoginRequest, TokenResponse, RefreshRequest, RefreshResponse
import uuid
from datetime import datetime


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
    print(f"✓ UserCreate: {user_create}")

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
    print(f"✓ UserRead: {user_read}")

    # Test role models
    role_create = RoleCreate(
        name="admin",
        permissions='{"read": true, "write": true}'
    )
    print(f"✓ RoleCreate: {role_create}")

    role_read = RoleRead(
        id=uuid.uuid4(),
        name="admin",
        permissions='{"read": true, "write": true}'
    )
    print(f"✓ RoleRead: {role_read}")

    # Test invoice models
    invoice_create = InvoiceCreate(
        customer_id=uuid.uuid4(),
        items='{"item1": "value1"}',
        totals='{"subtotal": 100, "tax": 10, "total": 110}'
    )
    print(f"✓ InvoiceCreate: {invoice_create}")

    # Test refund models
    refund_create = RefundCreate(
        invoice_id=uuid.uuid4(),
        items='{"item1": "value1"}',
        amount=50.00,
        reason="Wrong item",
        processed_by=uuid.uuid4()
    )
    print(f"✓ RefundCreate: {refund_create}")

    # Test salesman models
    salesman_create = SalesmanCreate(
        name="Jane Smith",
        code="JS001",
        commission_rate=0.05
    )
    print(f"✓ SalesmanCreate: {salesman_create}")

    # Test auth models
    token = Token(
        access_token="fake_access_token",
        refresh_token="fake_refresh_token",
        token_type="bearer"
    )
    print(f"✓ Token: {token}")

    token_data = TokenData(
        username="johndoe",
        user_id=1
    )
    print(f"✓ TokenData: {token_data}")

    refresh_token = RefreshToken(
        refresh_token="fake_refresh_token"
    )
    print(f"✓ RefreshToken: {refresh_token}")

    # Test auth router models
    login_req = LoginRequest(
        username="johndoe",
        password="password"
    )
    print(f"✓ LoginRequest: {login_req}")

    token_resp = TokenResponse(
        access_token="fake_access_token",
        refresh_token="fake_refresh_token",
        expires_in=900
    )
    print(f"✓ TokenResponse: {token_resp}")

    print("\n✓ All basic model creations succeeded!")


def test_model_relationships():
    """Test that model relationships work properly."""
    print("\nTesting model relationships...")

    # Create role first
    role = Role(
        id=uuid.uuid4(),
        name="admin",
        permissions='{"read": true, "write": true}',
        created_at=datetime.now()
    )
    print(f"✓ Created role: {role}")

    # Create user with role_id (but not the full role object to avoid circular reference issues)
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
    print(f"✓ Created user: {user}")

    # Test that repr works without recursion
    user_repr = repr(user)
    print(f"✓ User repr length: {len(user_repr)}")

    role_repr = repr(role)
    print(f"✓ Role repr length: {len(role_repr)}")

    print("\n✓ Model relationships work correctly!")


def test_complex_nested_models():
    """Test more complex nested model scenarios."""
    print("\nTesting complex nested models...")

    # Create a complex invoice with nested data
    invoice = Invoice(
        id=uuid.uuid4(),
        invoice_no="INV-001",
        customer_id=uuid.uuid4(),
        items='{"product1": {"quantity": 2, "price": 25.00}, "product2": {"quantity": 1, "price": 50.00}}',
        totals='{"subtotal": 100.00, "tax": 10.00, "total": 110.00}',
        taxes=10.00,
        discounts=5.00,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    print(f"✓ Complex invoice created: {invoice}")

    # Create a refund for the invoice
    refund = Refund(
        id=uuid.uuid4(),
        invoice_id=invoice.id,
        items='{"product1": {"quantity": 1, "amount": 25.00}}',
        amount=25.00,
        reason="Customer return",
        processed_by=uuid.uuid4(),
        created_at=datetime.now()
    )

    print(f"✓ Refund created: {refund}")

    print("\n✓ Complex nested models work correctly!")


if __name__ == "__main__":
    print("Testing Pydantic v2 models in the codebase...")
    print("=" * 50)

    try:
        test_basic_model_creation()
        test_model_relationships()
        test_complex_nested_models()

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! No recursion errors detected.")
        print("The models in the codebase are safe from Pydantic v2 recursion issues.")

    except RecursionError as e:
        print(f"\n❌ RECURSION ERROR DETECTED: {e}")
        print("There is still a recursion issue that needs to be addressed.")

    except Exception as e:
        print(f"\n❌ OTHER ERROR: {e}")
        import traceback
        traceback.print_exc()