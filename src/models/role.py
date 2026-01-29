from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid
import json

if TYPE_CHECKING:
    from .user import User

class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, max_length=50)  # admin, cashier, employee
    permissions: str = Field(default="{}")  # JSON string for permissions
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    # Relationship to Users
    users: List["User"] = Relationship(back_populates="role")

class RoleRead(SQLModel):
    id: uuid.UUID
    name: str
    permissions: str

class RoleCreate(SQLModel):
    name: str
    permissions: Optional[str] = "{}"

class RoleUpdate(SQLModel):
    name: Optional[str] = None
    permissions: Optional[str] = None