from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime, date, timedelta

from ..database.database import get_db
from ..models.user import User
from ..models.tournament import Tournament, TournamentSport, TournamentSource, TournamentCreate
from ..auth.session_auth import employee_required_from_session, get_current_user_from_session

router = APIRouter()


def _serialize(t: Tournament) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "sport": t.sport.value,
        "start_date": t.start_date.isoformat(),
        "end_date": t.end_date.isoformat() if t.end_date else None,
        "source": t.source.value,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }


@router.get("/upcoming")
async def get_upcoming_tournaments(
    days_ahead: int = 120,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Tournaments starting soon, or already underway - for the dashboard alert banner."""
    today = date.today()
    horizon = today + timedelta(days=max(1, min(days_ahead, 365)))

    statement = select(Tournament).where(
        Tournament.is_active == True,  # noqa: E712
        Tournament.start_date <= horizon,
        (Tournament.end_date.is_(None)) | (Tournament.end_date >= today),
    ).order_by(Tournament.start_date.asc())

    result = await db.execute(statement)
    tournaments = result.scalars().all()

    return {"data": [_serialize(t) for t in tournaments]}


@router.get("/list")
async def list_tournaments(
    search_string: Optional[str] = None,
    sport: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Full list of tracked tournaments (auto-synced + manual), for the management page."""
    if page < 1:
        page = 1
    if limit <= 0 or limit > 100:
        limit = 20
    skip = (page - 1) * limit

    conditions = []
    if search_string and search_string.strip():
        conditions.append(Tournament.name.ilike(f"%{search_string.strip()}%"))
    if sport:
        try:
            conditions.append(Tournament.sport == TournamentSport(sport.upper()))
        except ValueError:
            pass

    count_statement = select(func.count(Tournament.id))
    statement = select(Tournament)
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    # Nearest-to-start first, so whatever's coming up soonest is at the top
    statement = statement.order_by(Tournament.start_date.asc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    tournaments = result.scalars().all()

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        "data": [_serialize(t) for t in tournaments],
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


@router.post("/create")
async def create_tournament(
    tournament_data: TournamentCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Manually add a tournament the auto-sync doesn't know about (e.g. local Pakistan events)."""
    if not tournament_data.name or not tournament_data.name.strip():
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Tournament name is required")

    tournament = Tournament(
        name=tournament_data.name.strip(),
        sport=tournament_data.sport,
        start_date=tournament_data.start_date,
        end_date=tournament_data.end_date,
        source=TournamentSource.MANUAL,
        external_id=None,
        created_by=current_user.id,
    )
    db.add(tournament)
    await db.commit()
    await db.refresh(tournament)

    return {"success": True, "id": str(tournament.id), "message": "Tournament added successfully"}


@router.put("/update/{tournament_id}")
async def update_tournament(
    tournament_id: str,
    request_data: dict,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Edit a tournament's details, or deactivate it so it stops showing in the alert banner."""
    try:
        tournament_uuid = UUID(tournament_id)
    except ValueError:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid tournament ID format")

    result = await db.execute(select(Tournament).where(Tournament.id == tournament_uuid))
    tournament = result.scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Tournament not found")

    if "name" in request_data:
        new_name = (request_data.get("name") or "").strip()
        if not new_name:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Tournament name cannot be empty")
        tournament.name = new_name

    if "sport" in request_data and request_data.get("sport"):
        try:
            tournament.sport = TournamentSport(request_data["sport"].upper())
        except ValueError:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid sport")

    if "start_date" in request_data and request_data.get("start_date"):
        try:
            tournament.start_date = datetime.strptime(request_data["start_date"], "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid start_date, expected YYYY-MM-DD")

    if "end_date" in request_data:
        raw_end = request_data.get("end_date")
        if raw_end:
            try:
                tournament.end_date = datetime.strptime(raw_end, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid end_date, expected YYYY-MM-DD")
        else:
            tournament.end_date = None

    if "is_active" in request_data:
        tournament.is_active = bool(request_data.get("is_active"))

    tournament.updated_at = datetime.now()
    await db.commit()
    await db.refresh(tournament)

    return {"success": True, "id": str(tournament.id), **_serialize(tournament)}


@router.delete("/{tournament_id}")
async def delete_tournament(
    tournament_id: str,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """Delete a tournament record. Restricted to admin for accountability."""
    if current_user.role.name != "admin":
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only admin can delete tournament records")

    try:
        tournament_uuid = UUID(tournament_id)
    except ValueError:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Invalid tournament ID format")

    result = await db.execute(select(Tournament).where(Tournament.id == tournament_uuid))
    tournament = result.scalar_one_or_none()
    if not tournament:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Tournament not found")

    await db.delete(tournament)
    await db.commit()

    return {"success": True, "message": "Tournament deleted successfully"}


@router.post("/sync-now")
async def sync_now(
    current_user: User = Depends(get_current_user_from_session),
):
    """Manually trigger both source syncs immediately (admin only) - useful right after adding API keys."""
    if current_user.role.name != "admin":
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Only admin can trigger a manual sync")

    from ..services.sports_sync import run_cricket_sync_job, run_football_sync_job

    cricket_count = await run_cricket_sync_job()
    football_count = await run_football_sync_job()

    return {"success": True, "cricket_synced": cricket_count, "football_synced": football_count}


@router.get("/sync-status")
async def get_sync_status(
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Last-run status for each tournament data source, for the admin status strip."""
    from ..models.sync_status import SyncStatus

    result = await db.execute(select(SyncStatus))
    rows = {row.source.value: row for row in result.scalars().all()}

    def serialize(source: TournamentSource):
        row = rows.get(source.value)
        if not row:
            return {"source": source.value, "configured": False, "last_run_at": None, "success": None, "items_synced": 0, "error_message": None}
        return {
            "source": source.value,
            "configured": True,
            "last_run_at": row.last_run_at.isoformat(),
            "success": row.success,
            "items_synced": row.items_synced,
            "error_message": row.error_message,
        }

    return {
        "cricket": serialize(TournamentSource.CRICAPI),
        "football": serialize(TournamentSource.API_FOOTBALL),
    }
