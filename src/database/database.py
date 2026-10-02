from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from fastapi import Request, HTTPException, status
from typing import Dict
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from ..config.branches import BRANCHES, DEFAULT_BRANCH, BRANCH_COOKIE, configured_branches, current_branch

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def _create_engine(database_url: str) -> AsyncEngine:
    # For Neon with asyncpg, we need to handle SSL differently
    # Neon uses serverless architecture with connection pooling at proxy level
    if database_url and "neon.tech" in database_url:
        # For Neon connections, use appropriate pool settings for serverless architecture
        return create_async_engine(
            database_url,
            echo=False,  # Disable SQL logging for better performance
            pool_size=15,  # Increased pool for better concurrency
            max_overflow=25,  # Allow more overflow connections during peak
            pool_pre_ping=True,  # Re-enabled: verify connections before use
            pool_recycle=120,  # Recycle connections every 2 minutes (Neon serverless)
            pool_timeout=120,  # Increased timeout to prevent pool exhaustion
            connect_args={
                "server_settings": {
                    "application_name": "regal-pos-app"
                },
                "command_timeout": 120,  # Increased timeout for individual commands
                "ssl": "require",  # Explicit SSL for Neon
                "timeout": 120,  # asyncpg timeout
            }
        )
    # For local PostgreSQL, use regular connection with pool
    return create_async_engine(
        database_url,
        echo=False,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,  # Check connection health before use
        pool_recycle=3600,  # Recycle connections every hour
        pool_timeout=30,
        connect_args={
            "server_settings": {
                "application_name": "regal-pos-app"
            }
        }
    )


# One engine + session factory per branch whose DATABASE_URL is configured.
# A branch with no URL (e.g. DATABASE_URL_KARIMABAD not set on the server) is
# skipped with a warning; Light House is always required.
engines: Dict[str, AsyncEngine] = {}
session_factories: Dict[str, async_sessionmaker] = {}
for _branch in configured_branches():
    engines[_branch.code] = _create_engine(_branch.database_url)
    session_factories[_branch.code] = async_sessionmaker(engines[_branch.code], class_=AsyncSession, expire_on_commit=False)

for _code, _branch in BRANCHES.items():
    if _code not in engines:
        logger.warning("Branch %r disabled: %s is not set", _code, _branch.db_env)

# Default (Light House) engine/session - kept under the original names so
# startup, health checks and scripts that import them keep working unchanged.
engine = engines[DEFAULT_BRANCH]
AsyncSessionLocal = session_factories[DEFAULT_BRANCH]


def resolve_branch_code(request: Request) -> str:
    """Branch for this request from the `branch` cookie (missing -> Light House).
    Unknown or unconfigured branch is rejected, never silently mapped to another DB."""
    code = request.cookies.get(BRANCH_COOKIE) or DEFAULT_BRANCH
    if code not in BRANCHES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown branch")
    if code not in session_factories:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Branch is not available")
    return code


# Initialize cache on startup
async def init_cache():
    """Initialize Redis cache connection"""
    from ..utils.cache import cache
    await cache.connect()


async def close_cache():
    """Close Redis cache connection"""
    from ..utils.cache import cache
    await cache.disconnect()
SessionLocal = AsyncSessionLocal  # For compatibility with existing imports

async def get_db(request: Request):
    code = resolve_branch_code(request)
    request.state.branch = code
    current_branch.set(code)
    async with session_factories[code]() as session:
        yield session

# Function to create all tables
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)