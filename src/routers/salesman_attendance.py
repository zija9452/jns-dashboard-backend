from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date
from uuid import UUID

from ..database.database import get_db
from ..models.user import User
from ..services.salesman_attendance_service import SalesmanAttendanceService
from ..auth.session_auth import admin_cashier_employee_required_from_session, admin_required_from_session
from ..utils.firestore_signals import publish_signal

router = APIRouter()


# Frontend-compatible endpoints (MUST be before /{salesman_id} routes)

@router.get("/history")
async def get_attendance_history(
    skip: int = 0,
    limit: int = 20,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    salesman_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(admin_required_from_session()),  # Admin view of full attendance history
    db: AsyncSession = Depends(get_db)
):
    """
    Paginated salesman attendance history (which salesman was in/out on which
    day), for the admin-facing report view.
    """
    parsed_date_from = None
    parsed_date_to = None
    if date_from:
        try:
            parsed_date_from = date.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_from format, expected YYYY-MM-DD")
    if date_to:
        try:
            parsed_date_to = date.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date_to format, expected YYYY-MM-DD")

    parsed_salesman_id = None
    if salesman_id:
        try:
            parsed_salesman_id = UUID(salesman_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid salesman ID format")

    return await SalesmanAttendanceService.get_history(
        db,
        skip=skip,
        limit=limit,
        date_from=parsed_date_from,
        date_to=parsed_date_to,
        salesman_id=parsed_salesman_id,
        search=search,
    )


@router.get("/today")
async def get_today_attendance(
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Today's salesman attendance snapshot: pending / active / completed lists
    plus pending_count, used by the dashboard badge + popup.
    """
    return await SalesmanAttendanceService.get_today_overview(db)


@router.post("/{salesman_id}/check-in")
async def check_in_salesman(
    salesman_id: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a salesman as checked in for today.
    """
    try:
        salesman_uuid = UUID(salesman_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    try:
        attendance = await SalesmanAttendanceService.check_in(db, salesman_uuid, str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salesman is already checked in today"
        )

    await publish_signal("salesman_attendance")

    return {
        "salesman_id": str(attendance.salesman_id),
        "check_in_time": attendance.check_in_time.isoformat(),
    }


@router.post("/{salesman_id}/check-out")
async def check_out_salesman(
    salesman_id: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a salesman as checked out for today.
    """
    try:
        salesman_uuid = UUID(salesman_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    try:
        attendance = await SalesmanAttendanceService.check_out(db, salesman_uuid, str(current_user.id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await publish_signal("salesman_attendance")

    return {
        "salesman_id": str(attendance.salesman_id),
        "check_in_time": attendance.check_in_time.isoformat(),
        "check_out_time": attendance.check_out_time.isoformat(),
    }
