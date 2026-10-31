#!/usr/bin/env python3
"""
Batch = one lot (laat) reaching the warehouse, see BATCH_COSTING_PLAN.md sec 11:
- batches: numbered once for the whole warehouse (Batch 001, 002 ...), any number of
  vendors inside; no vendor / bill of its own any more.
- batch_vendors (new): one vendor inside one batch with its own bill total, freight,
  local cartage, markup %. Added at Stock In when the vendor's goods of that lot arrive.
- batch_images / product_batches: point at their batch vendor (bill pictures, and the
  product + vendor + batch line with its barcode).
- Existing batches (one per vendor) become a batch with that one vendor inside.

Runs on every branch database (schemas must stay identical). Idempotent - safe to run
multiple times. Stops on a branch where two batches already share a number.
"""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS batch_vendors (
        id UUID PRIMARY KEY,
        batch_id UUID NOT NULL REFERENCES batches(id),
        warehouse_vendor_id UUID NOT NULL REFERENCES warehouse_vendors(id),
        invoice_total NUMERIC(14, 2) NOT NULL,
        freight NUMERIC(12, 2) NOT NULL DEFAULT 0,
        cartage NUMERIC(12, 2) NOT NULL DEFAULT 0,
        markup_pct NUMERIC(6, 2) NOT NULL DEFAULT 0,
        created_by UUID NOT NULL REFERENCES users(id),
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        CONSTRAINT ux_batch_vendors_batch_vendor UNIQUE (batch_id, warehouse_vendor_id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_batch_vendors_batch_id ON batch_vendors (batch_id);",
    "CREATE INDEX IF NOT EXISTS ix_batch_vendors_warehouse_vendor_id ON batch_vendors (warehouse_vendor_id);",
    "ALTER TABLE batch_images ADD COLUMN IF NOT EXISTS batch_vendor_id UUID NULL REFERENCES batch_vendors(id) ON DELETE CASCADE;",
    "CREATE INDEX IF NOT EXISTS ix_batch_images_batch_vendor_id ON batch_images (batch_vendor_id);",
    "ALTER TABLE product_batches ADD COLUMN IF NOT EXISTS batch_vendor_id UUID NULL REFERENCES batch_vendors(id);",
    "CREATE INDEX IF NOT EXISTS ix_product_batches_batch_vendor_id ON product_batches (batch_vendor_id);",
    # The day this vendor's goods of the lot arrived (a lot made on the 30th, a vendor's goods on the 1st)
    "ALTER TABLE batch_vendors ADD COLUMN IF NOT EXISTS bill_date DATE NULL;",
]

# Old per-vendor batches -> a batch with that vendor inside (only rows not moved yet)
MOVE_DATA = [
    """
    INSERT INTO batch_vendors (id, batch_id, warehouse_vendor_id, invoice_total, freight, cartage,
                               markup_pct, created_by, created_at, updated_at)
    SELECT gen_random_uuid(), b.id, b.warehouse_vendor_id, COALESCE(b.invoice_total, 0), b.freight,
           b.cartage, b.markup_pct, b.created_by, b.created_at, b.updated_at
    FROM batches b
    WHERE b.warehouse_vendor_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM batch_vendors bv WHERE bv.batch_id = b.id);
    """,
    """
    UPDATE product_batches pb SET batch_vendor_id = bv.id
    FROM batch_vendors bv
    WHERE pb.batch_id = bv.batch_id AND pb.batch_vendor_id IS NULL;
    """,
    """
    UPDATE batch_images bi SET batch_vendor_id = bv.id
    FROM batch_vendors bv
    WHERE bi.batch_id = bv.batch_id AND bi.batch_vendor_id IS NULL;
    """,
    "UPDATE batches SET warehouse_vendor_id = NULL WHERE warehouse_vendor_id IS NOT NULL;",
    "UPDATE batch_vendors bv SET bill_date = b.batch_date FROM batches b WHERE bv.batch_id = b.id AND bv.bill_date IS NULL;",
]

AFTER = [
    "ALTER TABLE batches ALTER COLUMN warehouse_vendor_id DROP NOT NULL;",
    "ALTER TABLE batches ALTER COLUMN invoice_total DROP NOT NULL;",
    "ALTER TABLE batches DROP CONSTRAINT IF EXISTS ux_batches_vendor_batch_no;",
    # One number per batch in the whole warehouse (shops will count on their own)
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_batches_location_batch_no ON batches (location, batch_no);",
    # A product has one line per vendor inside a batch
    "ALTER TABLE product_batches DROP CONSTRAINT IF EXISTS ux_product_batches_product_batch;",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_product_batches_product_batch_vendor ON product_batches (product_id, batch_vendor_id);",
]


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        dups = await conn.fetch("""
            SELECT location, batch_no, count(*) FROM batches GROUP BY 1, 2 HAVING count(*) > 1
        """)
        if dups:
            print(f"[{env}] STOPPED - batch numbers repeat, fix them first: {[(d['location'], d['batch_no']) for d in dups]}")
            return
        async with conn.transaction():
            for sql in STATEMENTS:
                await conn.execute(sql)
            await conn.execute("ALTER TABLE batches ALTER COLUMN warehouse_vendor_id DROP NOT NULL;")
            for sql in MOVE_DATA:
                print(f"[{env}]   {await conn.execute(sql)}")
            for sql in AFTER:
                await conn.execute(sql)
        print(f"[{env}] batch lots + batch_vendors ready")
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
