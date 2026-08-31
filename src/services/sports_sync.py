"""
Daily sync of upcoming sports tournament dates (cricket + football) so the
shop can see, the same day a date becomes public, which tournaments are
coming up and stock the matching jerseys/kits ahead of time.

No live scores are pulled here on purpose - only schedule/date data, twice a
day (9am/9pm) plus on-demand via the admin "Sync Now" button. See CRICAPI_KEY
/ API_FOOTBALL_KEY in .env to enable each source; a source is silently
skipped (not an error) if its key isn't configured yet.
"""
import logging
from datetime import date, datetime, timedelta

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select, delete, and_, or_

from ..config.settings import settings
from ..models.tournament import Tournament, TournamentSource, TournamentSport
from ..models.sync_status import SyncStatus

logger = logging.getLogger(__name__)

CRICAPI_BASE = "https://api.cricapi.com/v1"
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"

# Football tournaments/leagues worth tracking for a shop that sells national
# team + club jerseys. IDs are api-football's stable league IDs.
FOOTBALL_LEAGUES = {
    1: "FIFA World Cup",
    4: "UEFA Euro Championship",
    9: "Copa America",
    6: "Africa Cup of Nations",
    7: "AFC Asian Cup",
    2: "UEFA Champions League",
    39: "Premier League",
    140: "La Liga",
}


def _parse_date(raw: str | None, reference: date | None = None):
    """Parse cricapi's date strings, which are sometimes full ISO dates and
    sometimes just 'Mon DD' with the year omitted (a known quirk of that API).
    When the year is missing, infer it as the nearest occurrence on/after
    `reference` (defaults to today; pass the resolved start_date when parsing
    an end_date so it anchors to the series itself, not today)."""
    if not raw:
        return None
    raw = raw.strip()
    reference = reference or date.today()

    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        pass

    try:
        month_day = datetime.strptime(raw[:6], "%b %d")
    except ValueError:
        return None

    candidate = date(reference.year, month_day.month, month_day.day)
    if candidate < reference - timedelta(days=30):
        candidate = date(reference.year + 1, month_day.month, month_day.day)
    return candidate


async def _upsert_tournament(db: AsyncSession, *, name: str, sport: TournamentSport,
                              start_date: date, end_date, source: TournamentSource, external_id: str):
    stmt = pg_insert(Tournament).values(
        name=name,
        sport=sport,
        start_date=start_date,
        end_date=end_date,
        source=source,
        external_id=external_id,
        is_active=True,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Tournament.source, Tournament.external_id],
        index_where=Tournament.external_id.isnot(None),
        set_={
            "name": stmt.excluded.name,
            "start_date": stmt.excluded.start_date,
            "end_date": stmt.excluded.end_date,
            "updated_at": datetime.now(),
        },
    )
    await db.execute(stmt)


async def sync_cricket(db: AsyncSession) -> int:
    """Pull upcoming cricket series (PSL, IPL, ICC events, Pakistan tours, etc.)."""
    api_key = settings.cricapi_key
    if not api_key:
        logger.info("CRICAPI_KEY not set, skipping cricket tournament sync")
        return 0

    upserted = 0
    cutoff = date.today() - timedelta(days=3)
    async with httpx.AsyncClient(timeout=20) as client:
        offset = 0
        for _ in range(4):  # a handful of pages covers the near-term calendar
            resp = await client.get(f"{CRICAPI_BASE}/series", params={"apikey": api_key, "offset": offset})
            if resp.status_code != 200:
                logger.warning(f"cricapi series fetch failed: {resp.status_code}")
                break
            series_list = (resp.json() or {}).get("data") or []
            if not series_list:
                break

            for series in series_list:
                start = _parse_date(series.get("startDate"))
                if not start or start < cutoff:
                    continue
                series_id = series.get("id")
                if not series_id:
                    continue
                await _upsert_tournament(
                    db,
                    name=(series.get("name") or "Cricket Series")[:150],
                    sport=TournamentSport.CRICKET,
                    start_date=start,
                    end_date=_parse_date(series.get("endDate"), reference=start),
                    source=TournamentSource.CRICAPI,
                    external_id=str(series_id),
                )
                upserted += 1

            if len(series_list) < 25:
                break
            offset += 25

    await db.commit()
    return upserted


async def sync_football(db: AsyncSession) -> int:
    """Pull the current/next season window for major football tournaments and leagues."""
    api_key = settings.api_football_key
    if not api_key:
        logger.info("API_FOOTBALL_KEY not set, skipping football tournament sync")
        return 0

    upserted = 0
    headers = {"x-apisports-key": api_key}
    today_iso = date.today().isoformat()
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        for league_id, name in FOOTBALL_LEAGUES.items():
            try:
                resp = await client.get(f"{API_FOOTBALL_BASE}/leagues", params={"id": league_id})
            except httpx.HTTPError as exc:
                logger.warning(f"api-football request failed for league {league_id}: {exc}")
                continue
            if resp.status_code != 200:
                logger.warning(f"api-football leagues fetch failed for {league_id}: {resp.status_code}")
                continue

            responses = (resp.json() or {}).get("response") or []
            if not responses:
                continue
            seasons = responses[0].get("seasons") or []
            upcoming = [s for s in seasons if s.get("end") and s["end"] >= today_iso]
            if not upcoming:
                continue
            season = sorted(upcoming, key=lambda s: s.get("start") or "")[0]

            start = _parse_date(season.get("start"))
            if not start:
                continue

            await _upsert_tournament(
                db,
                name=f"{name} {season.get('year', '')}".strip(),
                sport=TournamentSport.FOOTBALL,
                start_date=start,
                end_date=_parse_date(season.get("end")),
                source=TournamentSource.API_FOOTBALL,
                external_id=f"{league_id}-{season.get('year')}",
            )
            upserted += 1

    await db.commit()
    return upserted


async def delete_expired_tournaments(db: AsyncSession) -> int:
    """Drop tournaments whose date has passed - once a tournament is over it's no
    longer useful for restock planning, so there's no reason to keep it around.
    A tournament is expired once its end_date is in the past; if a series never
    got an end_date (a parsing gap upstream), fall back to 30 days past start_date
    so a still-running series with just a missing end date isn't deleted early."""
    today = date.today()
    stale_cutoff = today - timedelta(days=30)
    stmt = delete(Tournament).where(
        or_(
            and_(Tournament.end_date.isnot(None), Tournament.end_date < today),
            and_(Tournament.end_date.is_(None), Tournament.start_date < stale_cutoff),
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0


async def _record_sync_status(db: AsyncSession, *, source: TournamentSource, success: bool,
                               items_synced: int, error_message: str | None):
    result = await db.execute(select(SyncStatus).where(SyncStatus.source == source))
    row = result.scalar_one_or_none()
    if row is None:
        row = SyncStatus(source=source)
        db.add(row)
    row.last_run_at = datetime.now()
    row.success = success
    row.items_synced = items_synced
    row.error_message = error_message[:500] if error_message else None
    await db.commit()


async def run_cricket_sync_job() -> int:
    """Scheduler entry point for the cricket source (runs twice a day, 9am/9pm)."""
    from ..database.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            count = await sync_cricket(db)
            logger.info(f"Cricket tournament sync upserted {count} rows")
            await _record_sync_status(db, source=TournamentSource.CRICAPI, success=True,
                                       items_synced=count, error_message=None)
        except Exception as exc:
            logger.error(f"Cricket tournament sync failed: {exc}")
            await _record_sync_status(db, source=TournamentSource.CRICAPI, success=False,
                                       items_synced=0, error_message=str(exc))
            count = 0

        try:
            deleted = await delete_expired_tournaments(db)
            if deleted:
                logger.info(f"Deleted {deleted} expired tournaments")
        except Exception as exc:
            logger.error(f"Expired tournament cleanup failed: {exc}")

        return count


async def run_football_sync_job() -> int:
    """Scheduler entry point for the football source (runs twice a day, 9am/9pm)."""
    from ..database.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            count = await sync_football(db)
            logger.info(f"Football tournament sync upserted {count} rows")
            await _record_sync_status(db, source=TournamentSource.API_FOOTBALL, success=True,
                                       items_synced=count, error_message=None)
            return count
        except Exception as exc:
            logger.error(f"Football tournament sync failed: {exc}")
            await _record_sync_status(db, source=TournamentSource.API_FOOTBALL, success=False,
                                       items_synced=0, error_message=str(exc))
            return 0
