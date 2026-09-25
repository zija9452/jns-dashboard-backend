#!/usr/bin/env python3
"""
Creates the price_modifiers table: rupee adjustments (flat +/- or multiply) applied
on top of a category's base ideal_price for "modifier" sub-categories (e.g. Sleeves:
Full = +50, Size Type: Oversize+ = x2) - instead of needing a separate fixed price
for every combination.

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


async def add_price_modifiers_table():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'price_modifiers'
            );
        """)

        if not table_exists:
            await conn.execute("""
                CREATE TABLE price_modifiers (
                    id UUID PRIMARY KEY,
                    category_id UUID NOT NULL REFERENCES customer_categories(id),
                    sub_category VARCHAR(100) NOT NULL,
                    option_value VARCHAR(100) NOT NULL,
                    adjustment_type VARCHAR(20) NOT NULL DEFAULT 'flat',
                    value NUMERIC(10, 2) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(category_id, sub_category, option_value)
                );
            """)
            await conn.execute("CREATE INDEX ix_price_modifiers_category_id ON price_modifiers(category_id);")
            await conn.execute("CREATE INDEX ix_price_modifiers_sub_category ON price_modifiers(sub_category);")
            print("Created price_modifiers table (with indexes).")
        else:
            print("price_modifiers table already exists.")

        await conn.close()
        print("\nDone.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_price_modifiers_table())
