from sqlmodel import SQLModel
from sqlalchemy import Column, DateTime, func
from datetime import datetime
import uuid

class BaseUUIDModel(SQLModel):
    """
    Base model class that includes common fields for all models
    """
    id: uuid.UUID
    created_at: datetime = Column(DateTime(timezone=True), default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())