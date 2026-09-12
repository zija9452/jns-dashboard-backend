from sqlmodel import select
from sqlalchemy import and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, date

from ..models.salesman import Salesman
from ..models.salesman_attendance import SalesmanAttendance
from ..utils.audit_logger import audit_log


class SalesmanAttendanceService:
    """
    Service class for tracking daily salesman check-in / check-out timing.

    Every salesman gets at most one row per calendar day (enforced by a DB
    unique constraint), so "pending / active / completed" is always derived
    from a single consistent read rather than three separate queries that
    could drift apart under concurrent check-ins.

    Check-in/out timestamps are read from the DATABASE server's clock
    (Neon), converted to Pakistan time, rather than the app server's local
    clock - a local machine's date/time can be changed by whoever has
    access to it, but nobody in this app can influence what Neon's own
    clock reports.
    """

    @staticmethod
    async def _get_server_now(db: AsyncSession) -> datetime:
        """
        Current wall-clock time in Pakistan Standard Time (PKT), evaluated
        by the database server itself - never trust a value computed on
        the app server or supplied by a client for attendance timestamps.
        """
        result = await db.execute(text("SELECT (now() AT TIME ZONE 'Asia/Karachi')"))
        return result.scalar_one()

    @staticmethod
    async def get_today_overview(db: AsyncSession) -> Dict[str, Any]:
        """
        Single snapshot of today's attendance for every salesman, bucketed into
        pending (no row yet), active (checked in, not checked out) and
        completed (checked in and out).
        """
        today = (await SalesmanAttendanceService._get_server_now(db)).date()

        statement = (
            select(Salesman, SalesmanAttendance)
            .outerjoin(
                SalesmanAttendance,
                and_(
                    SalesmanAttendance.salesman_id == Salesman.id,
                    SalesmanAttendance.attendance_date == today,
                ),
            )
            .order_by(Salesman.name)
        )
        result = await db.execute(statement)
        rows = result.all()

        pending: List[Dict[str, Any]] = []
        active: List[Dict[str, Any]] = []
        completed: List[Dict[str, Any]] = []

        for salesman, attendance in rows:
            entry: Dict[str, Any] = {
                "salesman_id": str(salesman.id),
                "name": salesman.name,
                "branch": salesman.branch or "",
            }

            if attendance is None:
                pending.append(entry)
            elif attendance.check_out_time is None:
                pending_entry = dict(entry)
                pending_entry["check_in_time"] = attendance.check_in_time.isoformat()
                active.append(pending_entry)
            else:
                completed_entry = dict(entry)
                completed_entry["check_in_time"] = attendance.check_in_time.isoformat()
                completed_entry["check_out_time"] = attendance.check_out_time.isoformat()
                completed.append(completed_entry)

        return {
            "date": today.isoformat(),
            "pending": pending,
            "active": active,
            "completed": completed,
            "pending_count": len(pending),
        }

    @staticmethod
    async def check_in(db: AsyncSession, salesman_id: UUID, user_id: str) -> SalesmanAttendance:
        """
        Mark a salesman as checked in for today. Fails if a row already
        exists for (salesman_id, today) - either because this service already
        checked it or because the unique constraint rejects a race.
        """
        server_now = await SalesmanAttendanceService._get_server_now(db)
        today = server_now.date()

        existing_result = await db.execute(
            select(SalesmanAttendance).where(
                SalesmanAttendance.salesman_id == salesman_id,
                SalesmanAttendance.attendance_date == today,
            )
        )
        if existing_result.scalar_one_or_none():
            raise ValueError("Salesman is already checked in today")

        attendance = SalesmanAttendance(
            salesman_id=salesman_id,
            attendance_date=today,
            check_in_time=server_now,
            checked_in_by=UUID(user_id),
            created_at=server_now,
            updated_at=server_now,
        )

        db.add(attendance)
        await db.commit()
        await db.refresh(attendance)

        await audit_log(
            db=db,
            user_id=user_id,
            entity="SalesmanAttendance",
            action="CREATE",
            changes={
                "action": "CHECK_IN",
                "salesman_id": str(salesman_id),
                "check_in_time": attendance.check_in_time.isoformat(),
            },
        )

        return attendance

    @staticmethod
    async def check_out(db: AsyncSession, salesman_id: UUID, user_id: str) -> SalesmanAttendance:
        """
        Mark a salesman as checked out for today. Fails if the salesman has
        not checked in today, or has already checked out.
        """
        server_now = await SalesmanAttendanceService._get_server_now(db)
        today = server_now.date()

        result = await db.execute(
            select(SalesmanAttendance).where(
                SalesmanAttendance.salesman_id == salesman_id,
                SalesmanAttendance.attendance_date == today,
            )
        )
        attendance = result.scalar_one_or_none()

        if not attendance:
            raise ValueError("Salesman has not checked in today")

        if attendance.check_out_time is not None:
            raise ValueError("Salesman is already checked out today")

        attendance.check_out_time = server_now
        attendance.checked_out_by = UUID(user_id)
        attendance.updated_at = server_now

        await db.commit()
        await db.refresh(attendance)

        await audit_log(
            db=db,
            user_id=user_id,
            entity="SalesmanAttendance",
            action="UPDATE",
            changes={
                "action": "CHECK_OUT",
                "salesman_id": str(salesman_id),
                "check_out_time": attendance.check_out_time.isoformat(),
            },
        )

        return attendance

    @staticmethod
    async def get_history(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        salesman_id: Optional[UUID] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Paginated attendance history across all salesmen, for the admin view.
        """
        conditions = []
        if date_from:
            conditions.append(SalesmanAttendance.attendance_date >= date_from)
        if date_to:
            conditions.append(SalesmanAttendance.attendance_date <= date_to)
        if salesman_id:
            conditions.append(SalesmanAttendance.salesman_id == salesman_id)
        if search and search.strip():
            conditions.append(Salesman.name.ilike(f"%{search.strip()}%"))

        count_statement = (
            select(func.count())
            .select_from(SalesmanAttendance)
            .join(Salesman, Salesman.id == SalesmanAttendance.salesman_id)
        )
        statement = (
            select(SalesmanAttendance, Salesman)
            .join(Salesman, Salesman.id == SalesmanAttendance.salesman_id)
        )

        for condition in conditions:
            count_statement = count_statement.where(condition)
            statement = statement.where(condition)

        count_result = await db.execute(count_statement)
        total = count_result.scalar_one()

        statement = (
            statement
            .order_by(SalesmanAttendance.attendance_date.desc(), Salesman.name)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(statement)
        rows = result.all()

        today = (await SalesmanAttendanceService._get_server_now(db)).date()
        data: List[Dict[str, Any]] = []
        for attendance, salesman in rows:
            if attendance.check_out_time is not None:
                record_status = "COMPLETED"
            elif attendance.attendance_date == today:
                record_status = "IN_PROGRESS"
            else:
                record_status = "MISSED_CHECKOUT"

            data.append({
                "id": str(attendance.id),
                "salesman_id": str(salesman.id),
                "name": salesman.name,
                "branch": salesman.branch or "",
                "attendance_date": attendance.attendance_date.isoformat(),
                "check_in_time": attendance.check_in_time.isoformat(),
                "check_out_time": attendance.check_out_time.isoformat() if attendance.check_out_time else None,
                "status": record_status,
            })

        return {
            "data": data,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
