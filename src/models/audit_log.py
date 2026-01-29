from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid
import json
from enum import Enum

class AuditAction(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ACCESS = "ACCESS"

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entity: str = Field(max_length=50)  # Name of the entity (e.g., User, Product, Invoice)
    action: AuditAction  # Type of action performed
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")  # User who performed action
    changes: str = Field(default="{}")  # JSON string with details of changes made
    timestamp: datetime = Field(default_factory=lambda: datetime.now())

class AuditLogRead(SQLModel):
    id: uuid.UUID
    entity: str
    action: AuditAction
    user_id: Optional[uuid.UUID]
    changes: str
    timestamp: datetime

class AuditLogCreate(SQLModel):
    entity: str
    action: AuditAction
    user_id: Optional[uuid.UUID] = None
    changes: Optional[str] = "{}"