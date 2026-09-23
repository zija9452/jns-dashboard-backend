#!/usr/bin/env python3
"""
Status tracking (PENDING/FULFILLED/CANCELLED) is being dropped from Demand -
the team just wants to log and count demands, not manage a status lifecycle.
Drops demands.status, demands.fulfilled_at, demands.cancelled_at and the
now-unused demandstatus enum type.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))

if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")


async def remove_demand_status_columns():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        await conn.execute("ALTER TABLE demands DROP COLUMN IF EXISTS status;")
        print("Dropped demands.status")

        await conn.execute("ALTER TABLE demands DROP COLUMN IF EXISTS fulfilled_at;")
        print("Dropped demands.fulfilled_at")

        await conn.execute("ALTER TABLE demands DROP COLUMN IF EXISTS cancelled_at;")
        print("Dropped demands.cancelled_at")

        await conn.execute("DROP TYPE IF EXISTS demandstatus;")
        print("Dropped demandstatus enum type")

        await conn.close()
        print("demands status columns removed successfully!")

    except Exception as e:
        print(f"Error removing demand status columns: {e}")


if __name__ == "__main__":
    asyncio.run(remove_demand_status_columns())
