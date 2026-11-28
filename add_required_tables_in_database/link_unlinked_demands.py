#!/usr/bin/env python3
"""
Backfill: link every demand that has no demand_item_id to a demand_item.

Old demands typed as free text (no matching item in the list) were saved with
demand_item_id = NULL, so the /demand graph, Top Demanded Items and the item
search never saw them. For each such demand:
  - same name (case/space-insensitive) already in demand_items -> link to it
  - otherwise create the demand_item (name = demand text, category = demand's
    category) and link to it.

Runs on every branch database. Idempotent (re-running finds nothing to do).
Dry run by default; pass --apply to write.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

import asyncpg
from dotenv import find_dotenv, load_dotenv

load_dotenv()
load_dotenv(find_dotenv(usecwd=True))  # also the .env of the folder it is run from

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]
NAME_MAX = 150  # demand_items.name max_length


def norm(text: str) -> str:
    return " ".join((text or "").split()).lower()


async def backfill(env: str, url: str, apply: bool):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        items = await conn.fetch("SELECT id, name FROM demand_items")
        item_by_name = {norm(r["name"]): r["id"] for r in items}

        demands = await conn.fetch(
            "SELECT id, demand_text, category FROM demands "
            "WHERE demand_item_id IS NULL ORDER BY created_at"
        )
        print(f"[{env}] {len(items)} existing items, {len(demands)} unlinked demands")
        if not demands:
            return

        to_create = {}  # norm name -> (id, display name, category)
        links = []      # (demand_id, item_id)
        for d in demands:
            key = norm(d["demand_text"])
            if not key:
                print(f"[{env}]   skip empty text demand {d['id']}")
                continue
            item_id = item_by_name.get(key)
            if not item_id:
                if key not in to_create:
                    name = " ".join(d["demand_text"].split())[:NAME_MAX]
                    to_create[key] = (uuid.uuid4(), name, (d["category"] or None))
                item_id = to_create[key][0]
            links.append((d["id"], item_id))

        for _, name, category in to_create.values():
            print(f"[{env}]   new item: {name!r} ({category})")
        print(f"[{env}] would create {len(to_create)} items, link {len(links)} demands")

        if not apply:
            return
        async with conn.transaction():
            now = datetime.now()
            for item_id, name, category in to_create.values():
                await conn.execute(
                    "INSERT INTO demand_items (id, name, category, created_at) VALUES ($1, $2, $3, $4)",
                    item_id, name, category, now,
                )
            await conn.executemany(
                "UPDATE demands SET demand_item_id = $2 WHERE id = $1 AND demand_item_id IS NULL",
                links,
            )
        print(f"[{env}] DONE: created {len(to_create)} items, linked {len(links)} demands")
    finally:
        await conn.close()


async def main():
    apply = "--apply" in sys.argv
    print("MODE:", "APPLY" if apply else "DRY RUN (pass --apply to write)")
    for env in DB_ENVS:
        url = os.getenv(env)
        if not url:
            print(f"[{env}] not set - skipped")
            continue
        await backfill(env, url, apply)


if __name__ == "__main__":
    asyncio.run(main())
