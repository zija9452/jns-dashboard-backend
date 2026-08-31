from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid

from .tournament import TournamentSource


class SyncStatus(SQLModel, table=True):
    """Last-run status per tournament data source, for the admin status strip.
    One row per source (upserted on every run) - a full run history isn't kept
    here since job failures already go to the app's regular logs."""
    __tablename__ = "sync_status"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source: TournamentSource = Field(unique=True, index=True)
    last_run_at: datetime = Field(default_factory=datetime.now)
    success: bool = Field(default=True)
    items_synced: int = Field(default=0)
    error_message: Optional[str] = Field(default=None, max_length=500)
