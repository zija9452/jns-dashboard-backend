#!/usr/bin/env python3
"""
DTF logos on Quotation / Customer Invoice (Hoodie / Jacket lines):
- customer_categories.dtf_enabled: ticked on the Customer Category page; the DTF logos
  box shows only for these categories. Turned on here for "Hoodie Jacket" and "Jacket".
- dtf_pricing_settings: per-branch DTF rule (Rs per 0.5 m of roll, roll width, gap),
  edited on the Ideal Pricing page. Default row: 750 / 23" / 0.5".

Runs on every branch database (schemas must stay identical). Idempotent - safe to run
multiple times. The two categories are switched on only when the column is first
created, so a later untick on the Customer Category page isn't undone by a re-run.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]
DTF_CATEGORIES = ["Hoodie Jacket", "Jacket"]
# Same names as src/config/branches.py
BRANCH_NAMES = {
    "DATABASE_URL": "European Sports Light House",
    "DATABASE_URL_KARIMABAD": "European Sports Karim Abad",
}


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'customer_categories' AND column_name = 'dtf_enabled'
                );
            """)
            if not exists:
                await conn.execute(
                    "ALTER TABLE customer_categories ADD COLUMN dtf_enabled BOOLEAN NOT NULL DEFAULT false;"
                )
                result = await conn.execute(
                    "UPDATE customer_categories SET dtf_enabled = true WHERE main_category = ANY($1::text[]);",
                    DTF_CATEGORIES,
                )
                print(f"[{env}] Added customer_categories.dtf_enabled, turned on for {DTF_CATEGORIES} ({result})")
            else:
                print(f"[{env}] customer_categories.dtf_enabled already exists")

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS dtf_pricing_settings (
                    id UUID PRIMARY KEY,
                    price_per_half_meter NUMERIC(10, 2) NOT NULL DEFAULT 750.00,
                    roll_width_in NUMERIC(6, 2) NOT NULL DEFAULT 23.00,
                    gap_in NUMERIC(6, 2) NOT NULL DEFAULT 0.50,
                    branch VARCHAR(100) NOT NULL UNIQUE,
                    updated_at TIMESTAMP NOT NULL DEFAULT now()
                );
            """)
            branch = BRANCH_NAMES[env]  # = config/branches.py name, what the API looks the row up by
            inserted = await conn.execute("""
                INSERT INTO dtf_pricing_settings (id, price_per_half_meter, roll_width_in, gap_in, branch, updated_at)
                VALUES (gen_random_uuid(), 750.00, 23.00, 0.50, $1, now())
                ON CONFLICT (branch) DO NOTHING;
            """, branch)
            print(f"[{env}] dtf_pricing_settings ready for '{branch}' ({inserted})")
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
            print(f"[{env}] Error: {e}")
            import traceback
            traceback.print_exc()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
