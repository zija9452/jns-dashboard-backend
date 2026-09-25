#!/usr/bin/env python3
"""
Adds the min_qty column to ideal_prices so a single category/options combination
can carry multiple quantity-tier rates (e.g. 1-piece rate vs 5+ bulk rate).

Existing rows default to min_qty=1, which is correct as-is: every price already in
this table today was entered as the single-piece rate.

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


async def add_ideal_price_min_qty_column():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'ideal_prices'
                AND column_name = 'min_qty'
            );
        """)

        if not column_exists:
            await conn.execute("""
                ALTER TABLE ideal_prices
                ADD COLUMN min_qty INTEGER NOT NULL DEFAULT 1;
            """)
            print("Added min_qty column to ideal_prices table (existing rows defaulted to 1).")
        else:
            print("min_qty column already exists in ideal_prices table")

        await conn.close()
        print("\nDone.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_ideal_price_min_qty_column())
