from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import uuid
from enum import Enum

if TYPE_CHECKING:
    from .role import Role

class UserRole(str, Enum):
    ADMIN = "admin"
    CASHIER = "cashier"
    EMPLOYEE = "employee"
    WAREHOUSE = "warehouse"

class UserBase(SQLModel):
    full_name: Optional[str] = Field(default=None, max_length=100)
    username: str = Field(unique=True, min_length=3, max_length=30)
    role_id: Optional[uuid.UUID] = Field(default=None, foreign_key="roles.id")  # Make optional
    is_active: bool = Field(default=True)

class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    password_hash: str = Field(max_length=255)
    # WARNING: Storing original password for demonstration purposes only
    # This is a MAJOR SECURITY VULNERABILITY in production
    original_password: Optional[str] = Field(default=None, max_length=255)  # Plain text password
    phone: Optional[str] = Field(default=None, max_length=20)  # Phone number field
    address: Optional[str] = Field(default=None, max_length=200)  # Address field
    cnic: Optional[str] = Field(default=None, max_length=20)  # CNIC field
    branch: Optional[str] = Field(default=None, max_length=50)  # Branch field
    company_id: Optional[uuid.UUID] = Field(default=None)  # Company association (foreign key removed due to missing companies table)
    biometric_hash: Optional[str] = Field(default=None, max_length=255)  # For employee biometric data
    is_biometric_enabled: bool = Field(default=False)  # Whether biometric auth is enabled
    biometric_device_id: Optional[str] = Field(default=None, max_length=255)  # For device registration
    meta: Optional[str] = Field(default=None)  # JSON string for additional extensibility
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

    # Relationship to Role
    role: "Role" = Relationship(back_populates="users")

class UserRead(SQLModel):
    id: uuid.UUID
    full_name: Optional[str] = None
    username: str
    role_id: uuid.UUID
    phone: Optional[str] = None
    address: Optional[str] = None
    cnic: Optional[str] = None
    branch: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    is_biometric_enabled: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # WARNING: Including original password for demonstration purposes only
    # This is a MAJOR SECURITY VULNERABILITY in production
    original_password: Optional[str] = None  # Plain text password
    role_name: Optional[str] = None  # Include role name for display

class UserCreate(UserBase):
    password: str  # This will be stored in plain text for demonstration
    phone: Optional[str] = None
    address: Optional[str] = None
    cnic: Optional[str] = None
    branch: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    is_biometric_enabled: bool = False
    meta: Optional[str] = None
    role_name: Optional[str] = None  # Alternative: accept role name instead of UUID

class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[uuid.UUID] = None
    role_name: Optional[str] = None  # Alternative: accept role name for updates
    phone: Optional[str] = None
    address: Optional[str] = None
    cnic: Optional[str] = None
    branch: Optional[str] = None
    is_active: Optional[bool] = None