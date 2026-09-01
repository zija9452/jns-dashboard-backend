#!/usr/bin/env python3
"""
Script to add a sort_order column to demand_categories so the most
famous/most-requested sports can be pinned to the top of the dropdown
instead of always sorting alphabetically.
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

# Fame ranking (1 = most famous, shown first). Anything not listed here
# keeps whatever value it already has (new categories default to the end
# of the list via the API).
FAME_ORDER = [
    "Cricket",
    "Football",
    "Soccer",
    "Field Hockey",
    "Basketball",
    "Volleyball",
    "Badminton",
    "Tennis",
    "Squash",
    "Table Tennis",
    "Baseball",
    "American Football",
    "Rugby",
    "Ice Hockey",
    "Golf",
    "Boxing",
    "Wrestling",
    "Cycling",
    "Athletics",
    "Handball",
    "Netball",
    "Lacrosse",
    "Softball",
    "Fastpitch",
    "Flag Football",
    "7v7",
    "Bowling",
    "Fencing",
    "Cheerleading",
    "Snooker",
    "Weightlifting",
]

async def add_sort_order():
    """Add sort_order column and backfill fame-based ranking"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        await conn.execute("""
            ALTER TABLE demand_categories
            ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;
        """)
        print("Added sort_order column to demand_categories")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_demand_categories_sort_order
            ON demand_categories(sort_order);
        """)
        print("Created index on demand_categories.sort_order")

        for position, name in enumerate(FAME_ORDER, start=1):
            await conn.execute(
                "UPDATE demand_categories SET sort_order = $1 WHERE name = $2",
                position,
                name,
            )
        print(f"Backfilled sort_order for {len(FAME_ORDER)} known categories")

        await conn.close()
        print("demand_categories.sort_order migration completed successfully!")

    except Exception as e:
        print(f"Error adding sort_order to demand_categories: {e}")

if __name__ == "__main__":
    asyncio.run(add_sort_order())
