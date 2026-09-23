#!/usr/bin/env python3
"""
One-time cleanup: the initial demand_items backfill (add_demand_items_table.py)
matched on exact text, so items differing only by case (e.g. "Boxing Gloves"
vs "boxing gloves") became two separate catalog rows, splitting their demand
counts. This script:

1. Finds every group of demand_items that share the same lowercased name.
2. Keeps the item with the most linked demands (ties broken by the oldest
   item), re-links every other duplicate's demands to it, then deletes the
   now-empty duplicate rows.
3. Adds a case-insensitive UNIQUE index on demand_items(lower(name)) so this
   class of duplicate can never be created again (the existing exact-match
   UNIQUE constraint on name stays, this is additive).
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


async def merge_case_duplicates():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        groups = await conn.fetch("""
            SELECT LOWER(name) AS lower_name, array_agg(id ORDER BY id) AS ids, count(*) AS n
            FROM demand_items
            GROUP BY LOWER(name)
            HAVING count(*) > 1;
        """)
        print(f"Found {len(groups)} case-duplicate group(s)")

        for group in groups:
            item_ids = group["ids"]
            counts = await conn.fetch(
                """
                SELECT di.id, di.name, count(d.id) AS demand_count, di.created_at
                FROM demand_items di
                LEFT JOIN demands d ON d.demand_item_id = di.id
                WHERE di.id = ANY($1::uuid[])
                GROUP BY di.id
                ORDER BY demand_count DESC, di.created_at ASC;
                """,
                item_ids,
            )
            keeper = counts[0]
            duplicates = counts[1:]
            print(f"  Keeping '{keeper['name']}' ({keeper['id']}, {keeper['demand_count']} demands)")

            for dup in duplicates:
                relinked = await conn.execute(
                    "UPDATE demands SET demand_item_id = $1 WHERE demand_item_id = $2;",
                    keeper["id"], dup["id"],
                )
                await conn.execute("DELETE FROM demand_items WHERE id = $1;", dup["id"])
                print(f"    Merged '{dup['name']}' ({dup['id']}) into keeper: {relinked}")

        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_demand_items_name_ci
            ON demand_items (LOWER(name));
        """)
        print("Added case-insensitive unique index on demand_items(lower(name))")

        await conn.close()
        print("Case-duplicate merge completed successfully!")

    except Exception as e:
        print(f"Error merging case-duplicate demand items: {e}")


if __name__ == "__main__":
    asyncio.run(merge_case_duplicates())
