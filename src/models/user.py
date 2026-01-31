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

class UserBase(SQLModel):
    full_name: str = Field(max_length=100)
    email: str = Field(unique=True, max_length=255)
    username: str = Field(unique=True, min_length=3, max_length=30)
    role_id: uuid.UUID = Field(foreign_key="roles.id")
    is_active: bool = Field(default=True)

class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    password_hash: str = Field(max_length=255)
    meta: Optional[str] = Field(default=None)  # JSON string for extensibility
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)

    # Relationship to Role
    role: "Role" = Relationship(back_populates="users")

class UserRead(SQLModel):
    id: uuid.UUID
    full_name: str
    email: str
    username: str
    role_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

class UserCreate(UserBase):
    password: str
    meta: Optional[str] = None

class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    meta: Optional[str] = None