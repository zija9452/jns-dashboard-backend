#!/usr/bin/env python3
"""
Dye pricing (Quotation / Customer Invoice):
- customer_categories.dye_rate_single / dye_rate_qty: a dye line's rate multiplier when
  the category has 1-4 / 5-15 dye pcs (16+ = normal). Set on the Ideal Pricing page.
  Default 2 and 1.5.
- sub_categories[].dye_options (JSONB, no column): options ticked "Dye" on the Customer
  Category page. When the columns are first created, every option with "dye" in its
  name is ticked once, so existing Dye Fabric / Dye Light Speedo keep working; a later
  untick on the page isn't undone by a re-run.

Runs on every branch database (schemas must stay identical). Idempotent.
"""
import asyncio
import json
import os
import re

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]
DYE_NAME = re.compile(r"\bdye\b", re.IGNORECASE)


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'customer_categories' AND column_name = 'dye_rate_single'
                );
            """)
            if exists:
                print(f"[{env}] customer_categories.dye_rate_single already exists")
                return
            await conn.execute("""
                ALTER TABLE customer_categories
                    ADD COLUMN dye_rate_single NUMERIC(5, 2) NOT NULL DEFAULT 2,
                    ADD COLUMN dye_rate_qty NUMERIC(5, 2) NOT NULL DEFAULT 1.5;
            """)
            print(f"[{env}] Added customer_categories.dye_rate_single / dye_rate_qty")

            rows = await conn.fetch("SELECT id, main_category, sub_categories FROM customer_categories")
            for row in rows:
                subs = row["sub_categories"]
                if isinstance(subs, str):
                    subs = json.loads(subs)
                ticked = []
                for sc in subs or []:
                    sc["dye_options"] = [o for o in sc.get("options") or [] if DYE_NAME.search(o or "")]
                    ticked += sc["dye_options"]
                if ticked:
                    await conn.execute(
                        "UPDATE customer_categories SET sub_categories = $1::jsonb WHERE id = $2",
                        json.dumps(subs), row["id"],
                    )
                    print(f"[{env}]   {row['main_category']}: dye = {ticked}")
    finally:
        await conn.close()


async def main():
    for env in DB_ENVS:
        url = os.getenv(env)
        if not url:
            print(f"[{env}] not set - skipped")
            continue
        try:
            await migrate(env, url)
        except Exception as e:
            print(f"[{env}] FAILED: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
