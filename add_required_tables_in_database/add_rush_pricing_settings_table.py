#!/usr/bin/env python3
"""
Creates the rush_pricing_settings table: a single fixed rush-order surcharge
(Rs. per piece), applied across the whole order when "Rush Order" is selected
on a quotation/order. One row per branch, defaulting to Rs. 300/piece.

Idempotent - safe to run multiple times.
"""
import asyncio
import asyncpg
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))

if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

DEFAULT_BRANCH = "European Sports Light House"
DEFAULT_RATE = 300.00


async def add_rush_pricing_settings_table():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'rush_pricing_settings'
            );
        """)

        if not table_exists:
            await conn.execute("""
                CREATE TABLE rush_pricing_settings (
                    id UUID PRIMARY KEY,
                    price_per_piece NUMERIC(10, 2) NOT NULL DEFAULT 300.00,
                    branch VARCHAR(100) NOT NULL UNIQUE DEFAULT 'European Sports Light House',
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            print("Created rush_pricing_settings table.")
        else:
            print("rush_pricing_settings table already exists.")

        existing_row = await conn.fetchval(
            "SELECT id FROM rush_pricing_settings WHERE branch = $1;", DEFAULT_BRANCH
        )

        if not existing_row:
            await conn.execute(
                """
                INSERT INTO rush_pricing_settings (id, price_per_piece, branch)
                VALUES ($1, $2, $3);
                """,
                uuid.uuid4(), DEFAULT_RATE, DEFAULT_BRANCH
            )
            print(f"Inserted default rush rate: Rs. {DEFAULT_RATE}/piece for '{DEFAULT_BRANCH}'.")
        else:
            print(f"Default rush rate row already exists for '{DEFAULT_BRANCH}'.")

        await conn.close()
        print("\nDone.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_rush_pricing_settings_table())
