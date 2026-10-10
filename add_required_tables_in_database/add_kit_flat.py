#!/usr/bin/env python3
"""
Kit flat (Quotation / Customer Invoice):
- customer_categories.kit_role: "jersey" / "short" / "trouser" / NULL - what the category
  is in a team's kit. Set on the Customer Category page.
- customer_categories.kit_flat_charge: the kit's one flat charge (Jersey / Short), paid
  by the first of them added for a team that is one of our ready articles.

Runs on every branch database (schemas must stay identical). Idempotent.
"""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'customer_categories' AND column_name = 'kit_role'
            );
        """)
        if exists:
            print(f"[{env}] customer_categories.kit_role already exists")
            return
        await conn.execute("""
            ALTER TABLE customer_categories
                ADD COLUMN kit_role VARCHAR(10),
                ADD COLUMN kit_flat_charge NUMERIC(10, 2);
        """)
        print(f"[{env}] Added customer_categories.kit_role / kit_flat_charge")
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
