from sqlmodel import SQLModel, Field
from datetime import datetime
import uuid
from typing import Optional


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    session_token: str = Field(unique=True, index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    company_id: Optional[uuid.UUID] = Field(default=None)  # Removed foreign key constraint temporarily
    biometric_verified: bool = Field(default=False)


class UserSessionCreate(SQLModel):
    user_id: uuid.UUID
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    biometric_verified: bool = False


class UserSessionRead(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    session_token: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool
    company_id: Optional[uuid.UUID] = None
    biometric_verified: bool