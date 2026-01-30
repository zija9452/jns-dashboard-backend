from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# For Neon with asyncpg, we need to handle SSL differently
if DATABASE_URL and "neon.tech" in DATABASE_URL:
    # For Neon connections, use ssl=True in connect_args
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,
        connect_args={
            "server_settings": {
                "application_name": "regal-pos-app"
            }
        }
    )
else:
    # For local PostgreSQL, use regular connection
    engine = create_async_engine(
        DATABASE_URL,
        echo=True,
        connect_args={
            "server_settings": {
                "application_name": "regal-pos-app"
            }
        }
    )

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
SessionLocal = AsyncSessionLocal  # For compatibility with existing imports

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Function to create all tables
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)