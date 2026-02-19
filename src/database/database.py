from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# For Neon with asyncpg, we need to handle SSL differently
# Neon uses serverless architecture with connection pooling at proxy level
if DATABASE_URL and "neon.tech" in DATABASE_URL:
    # For Neon connections, use appropriate pool settings for serverless architecture
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,  # Enable SQL logging for debugging
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
else:
    # For local PostgreSQL, use regular connection with pool
    engine = create_async_engine(
        DATABASE_URL,
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

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
SessionLocal = AsyncSessionLocal  # For compatibility with existing imports

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Function to create all tables
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)