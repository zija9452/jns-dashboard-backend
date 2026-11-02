#!/usr/bin/env python3
"""
Product barcode counter (2026-11-02): the 5-digit sequence of auto barcodes
(prefix + 5 digits + check digit) is kept in barcode_counters and only moves forward when
a product is SAVED - so two people opening Add Product at once never fight over one
number at save, and a deleted product's barcode is never given again.

Starts from the highest sequence already used by auto barcodes (sequence < 10000, as
before - old imported price+cost barcodes sit above it and are skipped when reached).

Runs on every branch database. Idempotent - an existing counter is never lowered.
"""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = [("DATABASE_URL", "690"), ("DATABASE_URL_KARIMABAD", "691")]


async def main():
    for env, prefix in DB_ENVS:
        if not os.getenv(env):
            continue
        c = await asyncpg.connect(os.environ[env].replace("postgresql+asyncpg", "postgresql"))
        try:
            await c.execute("""
                CREATE TABLE IF NOT EXISTS barcode_counters (
                    prefix VARCHAR(10) PRIMARY KEY,
                    last_seq INTEGER NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT now()
                );
            """)
            used = await c.fetchval(f"""
                SELECT COALESCE(MAX(SUBSTRING(barcode FROM 4 FOR 5)::int), -1) FROM products
                WHERE barcode ~ '^{prefix}[0-9]{{6}}$' AND SUBSTRING(barcode FROM 4 FOR 5)::int < 10000
            """)
            await c.execute("""
                INSERT INTO barcode_counters (prefix, last_seq) VALUES ($1, $2)
                ON CONFLICT (prefix) DO UPDATE SET last_seq = GREATEST(barcode_counters.last_seq, EXCLUDED.last_seq),
                                                   updated_at = now()
            """, prefix, used)
            print(f"{env}: prefix {prefix} last_seq = {await c.fetchval('SELECT last_seq FROM barcode_counters WHERE prefix = $1', prefix)}")
        finally:
            await c.close()


if __name__ == "__main__":
    asyncio.run(main())
