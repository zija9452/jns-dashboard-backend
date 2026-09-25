#!/usr/bin/env python3
"""
Adds threshold_days to rush_pricing_settings: an order becomes rush automatically
when the customer's required-by date is within this many days of today (default 4).
This replaces a manual "Rush Order?" toggle - the cashier just enters the deadline,
the system derives rush status and charge from it.

Idempotent - safe to run multiple times.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))

if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

DEFAULT_THRESHOLD_DAYS = 4


async def add_rush_threshold_days_column():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'rush_pricing_settings'
                AND column_name = 'threshold_days'
            );
        """)

        if not column_exists:
            await conn.execute(f"""
                ALTER TABLE rush_pricing_settings
                ADD COLUMN threshold_days INTEGER NOT NULL DEFAULT {DEFAULT_THRESHOLD_DAYS};
            """)
            print(f"Added threshold_days column to rush_pricing_settings (existing rows defaulted to {DEFAULT_THRESHOLD_DAYS}).")
        else:
            print("threshold_days column already exists on rush_pricing_settings.")

        await conn.close()
        print("\nDone.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_rush_threshold_days_column())
