#!/usr/bin/env python3
"""
Script to create demand_items table and link it to demands, so repeated
demands for the same product can be counted accurately (used by the
/demand/stats graph and Top Demanded Items ranking).

Also backfills demand_items from the distinct demand_text values already
recorded in demands, and links each existing demand row to its item -
no existing data is lost or dropped, demand_text stays as-is.
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


async def add_demand_items_table():
    """Create demand_items table, link demands.demand_item_id, and backfill."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create demand_items table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS demand_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(150) NOT NULL UNIQUE,
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created demand_items table")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_demand_items_name ON demand_items(name);
        """)
        print("Created index on demand_items.name")

        # Link demands -> demand_items
        await conn.execute("""
            ALTER TABLE demands ADD COLUMN IF NOT EXISTS demand_item_id UUID REFERENCES demand_items(id);
        """)
        print("Added demands.demand_item_id column")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_demands_demand_item_id ON demands(demand_item_id);
        """)
        print("Created index on demands.demand_item_id")

        # Backfill: one demand_item per distinct (trimmed) demand_text, keep the
        # most recently used category for that text as the item's category.
        # IDs are generated here in Python rather than relying on the table's
        # gen_random_uuid() default, which this DB does not apply on a plain
        # multi-row INSERT...SELECT (the app normally supplies ids itself).
        import uuid as uuid_lib
        from datetime import datetime as dt

        distinct_rows = await conn.fetch("""
            SELECT DISTINCT ON (TRIM(demand_text))
                TRIM(demand_text) AS name,
                category
            FROM demands
            WHERE demand_item_id IS NULL AND TRIM(demand_text) <> ''
            ORDER BY TRIM(demand_text), created_at DESC;
        """)
        for row in distinct_rows:
            # id/created_at are supplied explicitly (not left to the column
            # defaults) since this table's defaults aren't reliably applied
            # on a plain parameterized INSERT against this database.
            await conn.execute(
                """
                INSERT INTO demand_items (id, name, category, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (name) DO NOTHING;
                """,
                uuid_lib.uuid4(),
                row["name"],
                row["category"],
                dt.now(),
            )
        print(f"Backfilled demand_items from {len(distinct_rows)} existing demand_text values")

        link_result = await conn.execute("""
            UPDATE demands
            SET demand_item_id = demand_items.id
            FROM demand_items
            WHERE demands.demand_item_id IS NULL
              AND TRIM(demands.demand_text) = demand_items.name;
        """)
        print(f"Linked existing demands to demand_items: {link_result}")

        await conn.close()
        print("demand_items table + backfill completed successfully!")

    except Exception as e:
        print(f"Error creating demand_items table: {e}")


if __name__ == "__main__":
    asyncio.run(add_demand_items_table())
