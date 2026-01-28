import pytest
from datetime import datetime
from uuid import UUID
import uuid
from src.models.role import Role, RoleCreate, RoleUpdate

def test_role_creation():
    """Test creating a new role instance"""
    role_id = uuid.uuid4()

    role = Role(
        id=role_id,
        name="admin",
        permissions='{"all": true, "users": true, "products": true}'
    )

    assert role.id == role_id
    assert role.name == "admin"
    assert role.permissions == '{"all": true, "users": true, "products": true}'
    assert isinstance(role.created_at, datetime)

def test_role_create_schema():
    """Test RoleCreate schema"""
    role_create = RoleCreate(
        name="cashier",
        permissions='{"pos": true, "view_inventory": true}'
    )

    assert role_create.name == "cashier"
    assert role_create.permissions == '{"pos": true, "view_inventory": true}'

def test_role_update_schema():
    """Test RoleUpdate schema"""
    role_update = RoleUpdate(
        name="updated_role",
        permissions='{"new_permissions": true}'
    )

    assert role_update.name == "updated_role"
    assert role_update.permissions == '{"new_permissions": true}'

def test_different_role_types():
    """Test different role types"""
    admin_role = Role(
        id=uuid.uuid4(),
        name="admin",
        permissions='{"all_access": true}'
    )
    cashier_role = Role(
        id=uuid.uuid4(),
        name="cashier",
        permissions='{"pos_access": true, "limited_admin": false}'
    )
    employee_role = Role(
        id=uuid.uuid4(),
        name="employee",
        permissions='{"read_only": true, "limited_access": true}'
    )

    assert admin_role.name == "admin"
    assert cashier_role.name == "cashier"
    assert employee_role.name == "employee"

def test_role_optional_fields():
    """Test role with empty permissions"""
    role_id = uuid.uuid4()

    role = Role(
        id=role_id,
        name="minimal_role"
        # permissions defaults to "{}"
    )

    assert role.id == role_id
    assert role.name == "minimal_role"
    assert role.permissions == "{}"  # Default value