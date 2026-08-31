from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, date
import uuid
from enum import Enum


class TournamentSport(str, Enum):
    CRICKET = "CRICKET"
    FOOTBALL = "FOOTBALL"
    TENNIS = "TENNIS"


class TournamentSource(str, Enum):
    CRICAPI = "CRICAPI"
    API_FOOTBALL = "API_FOOTBALL"
    MANUAL = "MANUAL"


class Tournament(SQLModel, table=True):
    __tablename__ = "tournaments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=150)
    sport: TournamentSport = Field(index=True)
    start_date: date = Field(index=True)
    end_date: Optional[date] = Field(default=None)
    source: TournamentSource = Field(default=TournamentSource.MANUAL)
    external_id: Optional[str] = Field(default=None, max_length=100, index=True)
    is_active: bool = Field(default=True)
    created_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now)


class TournamentRead(SQLModel):
    id: uuid.UUID
    name: str
    sport: TournamentSport
    start_date: date
    end_date: Optional[date]
    source: TournamentSource
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TournamentCreate(SQLModel):
    name: str
    sport: TournamentSport
    start_date: date
    end_date: Optional[date] = None


class TournamentUpdate(SQLModel):
    name: Optional[str] = None
    sport: Optional[TournamentSport] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
