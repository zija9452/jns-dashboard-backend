#!/usr/bin/env python3
"""
Shop batches (LH / KA), BATCH_COSTING_PLAN.md sec 12: same dhaancha as warehouse lots -
a batch (location 'shop') with vendors inside - but the vendors are shop vendors
(`vendors` table) and there is no bill (no total / freight / cartage / markup).

- vendors.vendor_code: 3+ digit code for shop batch barcodes (product + vendor code +
  batch no). Same name = same code in every branch (J&S Sports = 001).
- batch_vendors.vendor_id: the shop vendor of a shop batch (warehouse_vendor_id stays
  for warehouse batches; one of the two is set).

Runs on every branch database (schemas must stay identical). Idempotent - safe to run
multiple times.
"""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]

STATEMENTS = [
    "ALTER TABLE vendors ADD COLUMN IF NOT EXISTS vendor_code VARCHAR(10) NULL;",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_vendors_vendor_code ON vendors (vendor_code) WHERE vendor_code IS NOT NULL;",
    "ALTER TABLE batch_vendors ADD COLUMN IF NOT EXISTS vendor_id UUID NULL REFERENCES vendors(id);",
    "ALTER TABLE batch_vendors ALTER COLUMN warehouse_vendor_id DROP NOT NULL;",
    "CREATE INDEX IF NOT EXISTS ix_batch_vendors_vendor_id ON batch_vendors (vendor_id);",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_batch_vendors_batch_shop_vendor ON batch_vendors (batch_id, vendor_id) WHERE vendor_id IS NOT NULL;",
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_batch_vendors_one_vendor') THEN
            ALTER TABLE batch_vendors ADD CONSTRAINT ck_batch_vendors_one_vendor
                CHECK ((warehouse_vendor_id IS NULL) <> (vendor_id IS NULL));
        END IF;
    END $$;
    """,
]


def code_for(n: int) -> str:
    # Same as models/warehouse_vendor.vendor_code_for
    if n < 900:
        return f"{n:03d}"
    nines, value = divmod(n - 900, 900)
    return "9" * (nines + 1) + f"{value:03d}"


def url(env: str) -> str:
    return os.environ[env].replace("postgresql+asyncpg", "postgresql")


async def main():
    conns = {env: await asyncpg.connect(url(env)) for env in DB_ENVS if os.getenv(env)}
    try:
        for env, c in conns.items():
            for sql in STATEMENTS:
                await c.execute(sql)
            print(f"{env}: schema ok")

        # Codes by name, same in every branch: names already coded keep theirs, the rest
        # get the next numbers in order of their first creation in any branch
        coded, first_seen = {}, {}
        for c in conns.values():
            for r in await c.fetch("SELECT name, vendor_code, created_at FROM vendors"):
                key = (r["name"] or "").strip().lower()
                if r["vendor_code"]:
                    coded.setdefault(key, r["vendor_code"])
                if key not in first_seen or r["created_at"] < first_seen[key]:
                    first_seen[key] = r["created_at"]
        # code -> number (inverse of code_for)
        used = {int(code) if len(code) == 3 else 900 * (len(code) - 3) + int(code[-3:]) for code in coded.values()}
        n = max(used, default=0)
        for key in sorted((k for k in first_seen if k not in coded), key=lambda k: first_seen[k]):
            n += 1
            coded[key] = code_for(n)

        for env, c in conns.items():
            async with c.transaction():
                for r in await c.fetch("SELECT id, name FROM vendors WHERE vendor_code IS NULL"):
                    code = coded[(r["name"] or "").strip().lower()]
                    await c.execute("UPDATE vendors SET vendor_code = $1 WHERE id = $2", code, r["id"])
            rows = await c.fetch("SELECT name, vendor_code FROM vendors ORDER BY vendor_code")
            print(f"{env}: " + ", ".join(f"{r['name']} = {r['vendor_code']}" for r in rows))
    finally:
        for c in conns.values():
            await c.close()


if __name__ == "__main__":
    asyncio.run(main())
