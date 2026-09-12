from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint
from typing import Optional
from datetime import datetime, date
import uuid


class SalesmanAttendance(SQLModel, table=True):
    """
    One row per salesman per calendar day, tracking check-in / check-out timing.
    The (salesman_id, attendance_date) unique constraint is the source of truth
    for "has this salesman already checked in today" - state is never duplicated
    in a separate status column, it is always derived from the timestamps.
    """
    __tablename__ = "salesman_attendance"
    __table_args__ = (
        UniqueConstraint("salesman_id", "attendance_date", name="uq_salesman_attendance_salesman_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    salesman_id: uuid.UUID = Field(foreign_key="salesmen.id", nullable=False, index=True)
    attendance_date: date = Field(nullable=False, index=True)
    check_in_time: datetime = Field(nullable=False)
    check_out_time: Optional[datetime] = Field(default=None)
    checked_in_by: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    checked_out_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), nullable=False)


class SalesmanAttendanceRead(SQLModel):
    id: uuid.UUID
    salesman_id: uuid.UUID
    attendance_date: date
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
