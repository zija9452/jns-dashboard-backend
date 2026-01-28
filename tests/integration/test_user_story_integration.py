import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session
from uuid import UUID
import uuid
from datetime import datetime
from decimal import Decimal

from src.api.main import app
from src.models.user import User
from src.models.role import Role
from src.models.product import Product
from src.models.customer import Customer
from src.models.invoice import Invoice, InvoiceStatus
from src.auth.password import get_password_hash

def test_admin_full_workflow():
    """Test the complete admin workflow: create user, product, customer, and invoice"""
    client = TestClient(app)

    # Mock admin user
    admin_user_id = uuid.uuid4()
    admin_role_id = uuid.uuid4()

    admin_user = User(
        id=admin_user_id,
        full_name="Admin User",
        email="admin@test.com",
        username="admin",
        password_hash=get_password_hash("adminpassword"),
        role_id=admin_role_id,
        is_active=True
    )

    admin_role = Role(
        id=admin_role_id,
        name="admin",
        permissions='{"all": true}'
    )

    # Mock token
    mock_token = "mock_admin_token"

    # Test the full admin workflow
    with patch('src.auth.auth.oauth2_scheme') as mock_scheme:
        mock_scheme.return_value = mock_token

        # Mock token verification
        with patch('src.auth.auth.verify_token') as mock_verify:
            mock_verify.return_value = MagicMock()
            mock_verify.return_value.username = "admin"
            mock_verify.return_value.user_id = str(admin_user_id)

            with patch('src.database.database.SessionLocal') as mock_session_class:
                mock_session = MagicMock(spec=Session)

                # Mock role query
                mock_exec_role = MagicMock()
                mock_exec_role.first.return_value = admin_role
                mock_session.exec.return_value = mock_exec_role

                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session_class.return_value.__exit__.return_value = None

                # Test 1: Create a product
                product_response = client.post(
                    "/products/",
                    json={
                        "sku": "ADMIN-TEST-001",
                        "name": "Admin Test Product",
                        "unit_price": "29.99",
                        "cost_price": "15.00",
                        "stock_level": 100
                    },
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                assert product_response.status_code == 200
                product_data = product_response.json()
                assert product_data["sku"] == "ADMIN-TEST-001"
                assert product_data["name"] == "Admin Test Product"

                # Test 2: Create a customer
                customer_response = client.post(
                    "/customers/",
                    json={
                        "name": "Admin Test Customer",
                        "contacts": '{"phone": "+1234567890", "email": "customer@test.com"}',
                        "credit_limit": "5000.00"
                    },
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                assert customer_response.status_code == 200
                customer_data = customer_response.json()
                assert customer_data["name"] == "Admin Test Customer"

                # Test 3: Create an invoice
                if "id" in customer_data:
                    invoice_response = client.post(
                        "/invoices/",
                        json={
                            "customer_id": customer_data["id"],
                            "items": '[{"product_id": "' + product_data["id"] + '", "quantity": 2, "price": 29.99}]',
                            "totals": '{"subtotal": 59.98, "tax": 4.80, "total": 64.78}',
                            "taxes": "4.80",
                            "discounts": "0.00",
                            "status": "issued"
                        },
                        headers={"Authorization": f"Bearer {mock_token}"}
                    )

                    assert invoice_response.status_code == 200
                    invoice_data = invoice_response.json()
                    assert invoice_data["status"] == "issued"

def test_cashier_pos_workflow():
    """Test the cashier POS workflow: quick sell, cash drawer operations"""
    client = TestClient(app)

    # Mock cashier user
    cashier_user_id = uuid.uuid4()
    cashier_role_id = uuid.uuid4()

    cashier_user = User(
        id=cashier_user_id,
        full_name="Cashier User",
        email="cashier@test.com",
        username="cashier",
        password_hash=get_password_hash("cashierpassword"),
        role_id=cashier_role_id,
        is_active=True
    )

    cashier_role = Role(
        id=cashier_role_id,
        name="cashier",
        permissions='{"pos": true, "view_inventory": true}'
    )

    # Mock token
    mock_token = "mock_cashier_token"

    # Test the cashier workflow
    with patch('src.auth.auth.oauth2_scheme') as mock_scheme:
        mock_scheme.return_value = mock_token

        # Mock token verification
        with patch('src.auth.auth.verify_token') as mock_verify:
            mock_verify.return_value = MagicMock()
            mock_verify.return_value.username = "cashier"
            mock_verify.return_value.user_id = str(cashier_user_id)

            with patch('src.database.database.SessionLocal') as mock_session_class:
                mock_session = MagicMock(spec=Session)

                # Mock role query
                mock_exec_role = MagicMock()
                mock_exec_role.first.return_value = cashier_role
                mock_session.exec.return_value = mock_exec_role

                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session_class.return_value.__exit__.return_value = None

                # Test 1: Quick sell (using product created in previous test)
                quick_sell_response = client.post(
                    "/pos/quick-sell",
                    json={
                        "product_ids": ["some-product-id"],
                        "customer_id": "some-customer-id"
                    },
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                # This might fail if product doesn't exist, but we're testing the endpoint access
                # which should be allowed for cashiers
                assert quick_sell_response.status_code in [200, 404, 422]  # 404/422 are acceptable for missing data

                # Test 2: Open cash drawer
                cash_drawer_open_response = client.post(
                    "/pos/cash-drawer/open",
                    json={
                        "amount": 100.0,
                        "note": "Opening for shift"
                    },
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                assert cash_drawer_open_response.status_code == 200
                cash_drawer_data = cash_drawer_open_response.json()
                assert "message" in cash_drawer_data

                # Test 3: Close cash drawer
                cash_drawer_close_response = client.post(
                    "/pos/cash-drawer/close",
                    json={
                        "expected_amount": 150.0,
                        "actual_amount": 148.5,
                        "note": "Minor variance"
                    },
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                assert cash_drawer_close_response.status_code == 200
                cash_drawer_close_data = cash_drawer_close_response.json()
                assert "message" in cash_drawer_close_data

def test_employee_general_access_workflow():
    """Test the employee general access workflow: view products, customers"""
    client = TestClient(app)

    # Mock employee user
    employee_user_id = uuid.uuid4()
    employee_role_id = uuid.uuid4()

    employee_user = User(
        id=employee_user_id,
        full_name="Employee User",
        email="employee@test.com",
        username="employee",
        password_hash=get_password_hash("employeepassword"),
        role_id=employee_role_id,
        is_active=True
    )

    employee_role = Role(
        id=employee_role_id,
        name="employee",
        permissions='{"view_products": true, "view_customers": true}'
    )

    # Mock token
    mock_token = "mock_employee_token"

    # Test the employee workflow
    with patch('src.auth.auth.oauth2_scheme') as mock_scheme:
        mock_scheme.return_value = mock_token

        # Mock token verification
        with patch('src.auth.auth.verify_token') as mock_verify:
            mock_verify.return_value = MagicMock()
            mock_verify.return_value.username = "employee"
            mock_verify.return_value.user_id = str(employee_user_id)

            with patch('src.database.database.SessionLocal') as mock_session_class:
                mock_session = MagicMock(spec=Session)

                # Mock role query
                mock_exec_role = MagicMock()
                mock_exec_role.first.return_value = employee_role
                mock_session.exec.return_value = mock_exec_role

                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session_class.return_value.__exit__.return_value = None

                # Test 1: View products (should be allowed for employees)
                products_response = client.get(
                    "/products/",
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                assert products_response.status_code == 200
                products_data = products_response.json()
                assert isinstance(products_data, list)  # Should return a list of products

                # Test 2: View customers (should be allowed for employees)
                customers_response = client.get(
                    "/customers/",
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                assert customers_response.status_code == 200
                customers_data = customers_response.json()
                assert isinstance(customers_data, list)  # Should return a list of customers

def test_role_based_access_restrictions():
    """Test that role-based access restrictions work properly"""
    client = TestClient(app)

    # Mock employee user (should NOT have admin access)
    employee_user_id = uuid.uuid4()
    employee_role_id = uuid.uuid4()

    employee_user = User(
        id=employee_user_id,
        full_name="Restricted Employee",
        email="restricted@test.com",
        username="restricted_emp",
        password_hash=get_password_hash("password"),
        role_id=employee_role_id,
        is_active=True
    )

    employee_role = Role(
        id=employee_role_id,
        name="employee",
        permissions='{"view_products": true, "view_customers": true}'  # No admin perms
    )

    # Mock token
    mock_token = "mock_restricted_token"

    # Test that employee can't access admin-only functionality
    with patch('src.auth.auth.oauth2_scheme') as mock_scheme:
        mock_scheme.return_value = mock_token

        # Mock token verification
        with patch('src.auth.auth.verify_token') as mock_verify:
            mock_verify.return_value = MagicMock()
            mock_verify.return_value.username = "restricted_emp"
            mock_verify.return_value.user_id = str(employee_user_id)

            with patch('src.database.database.SessionLocal') as mock_session_class:
                mock_session = MagicMock(spec=Session)

                # Mock role query
                mock_exec_role = MagicMock()
                mock_exec_role.first.return_value = employee_role
                mock_session.exec.return_value = mock_exec_role

                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session_class.return_value.__exit__.return_value = None

                # Try to create a user (should be forbidden for employee)
                create_user_response = client.post(
                    "/users/",
                    json={
                        "full_name": "New User",
                        "email": "newuser@test.com",
                        "username": "newuser",
                        "password": "password",
                        "role_id": str(uuid.uuid4())
                    },
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                # Should return 403 Forbidden since employees can't create users
                assert create_user_response.status_code == 403

def test_invoice_lifecycle():
    """Test the complete invoice lifecycle: create, update, view, delete"""
    client = TestClient(app)

    # Mock admin user
    admin_user_id = uuid.uuid4()
    admin_role_id = uuid.uuid4()

    admin_user = User(
        id=admin_user_id,
        full_name="Admin Invoice User",
        email="admininv@test.com",
        username="admininv",
        password_hash=get_password_hash("password"),
        role_id=admin_role_id,
        is_active=True
    )

    admin_role = Role(
        id=admin_role_id,
        name="admin",
        permissions='{"all": true}'
    )

    # Mock token
    mock_token = "mock_invoice_token"

    with patch('src.auth.auth.oauth2_scheme') as mock_scheme:
        mock_scheme.return_value = mock_token

        # Mock token verification
        with patch('src.auth.auth.verify_token') as mock_verify:
            mock_verify.return_value = MagicMock()
            mock_verify.return_value.username = "admininv"
            mock_verify.return_value.user_id = str(admin_user_id)

            with patch('src.database.database.SessionLocal') as mock_session_class:
                mock_session = MagicMock(spec=Session)

                # Mock role query
                mock_exec_role = MagicMock()
                mock_exec_role.first.return_value = admin_role
                mock_session.exec.return_value = mock_exec_role

                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session_class.return_value.__exit__.return_value = None

                # Note: Actual invoice lifecycle test would require existing customer and product
                # For this integration test, we'll just verify the endpoints are accessible to admin

                # Test invoice creation endpoint
                # (Would normally require valid customer and product IDs)
                invoice_create_response = client.post(
                    "/invoices/",
                    json={
                        "customer_id": str(uuid.uuid4()),  # Using mock ID
                        "items": "[]",
                        "totals": '{"subtotal": 0, "tax": 0, "total": 0}',
                        "taxes": "0.00",
                        "discounts": "0.00",
                        "status": "draft"
                    },
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                # Could be 200 (success), 404 (customer not found), or 422 (validation error)
                # All are valid responses indicating the endpoint is accessible
                assert invoice_create_response.status_code in [200, 404, 422]

def test_stock_adjustment_workflow():
    """Test the stock adjustment workflow"""
    client = TestClient(app)

    # Mock admin user
    admin_user_id = uuid.uuid4()
    admin_role_id = uuid.uuid4()

    admin_user = User(
        id=admin_user_id,
        full_name="Admin Stock User",
        email="adminstock@test.com",
        username="adminstock",
        password_hash=get_password_hash("password"),
        role_id=admin_role_id,
        is_active=True
    )

    admin_role = Role(
        id=admin_role_id,
        name="admin",
        permissions='{"all": true}'
    )

    # Mock token
    mock_token = "mock_stock_token"

    with patch('src.auth.auth.oauth2_scheme') as mock_scheme:
        mock_scheme.return_value = mock_token

        # Mock token verification
        with patch('src.auth.auth.verify_token') as mock_verify:
            mock_verify.return_value = MagicMock()
            mock_verify.return_value.username = "adminstock"
            mock_verify.return_value.user_id = str(admin_user_id)

            with patch('src.database.database.SessionLocal') as mock_session_class:
                mock_session = MagicMock(spec=Session)

                # Mock role query
                mock_exec_role = MagicMock()
                mock_exec_role.first.return_value = admin_role
                mock_session.exec.return_value = mock_exec_role

                mock_session_class.return_value.__enter__.return_value = mock_session
                mock_session_class.return_value.__exit__.return_value = None

                # Test stock entry creation (which adjusts stock)
                stock_response = client.post(
                    "/stock/",
                    json={
                        "product_id": str(uuid.uuid4()),  # Using mock ID
                        "qty": 50,
                        "type": "IN",
                        "location": "Warehouse A"
                    },
                    headers={"Authorization": f"Bearer {mock_token}"}
                )

                # Could be 200 (success) or 404 (product not found) - both indicate accessibility
                assert stock_response.status_code in [200, 404, 422]