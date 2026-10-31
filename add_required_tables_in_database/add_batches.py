#!/usr/bin/env python3
"""
Batch costing - Phase 1 (warehouse batch page), see BATCH_COSTING_PLAN.md:
- warehouse_vendors.vendor_no / vendor_code: 1 -> "001" ... (never reused); existing
  vendors get numbers in the order they were created.
- warehouse_vendors name unique, ignoring case and outer spaces.
- batches: one vendor bill (invoice total, freight, cartage, markup %), numbered per vendor.
- batch_images: pictures of the bill.
- Phase 2: product_batches (product in a batch: barcode, cost, landed cost, selling
  price, stock) and stock_entries.product_batch_id.

Runs on every branch database (schemas must stay identical). Idempotent - safe to run
multiple times. Stops on a branch whose vendor names already repeat (fix them first).
"""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]


def vendor_code_for(vendor_no: int) -> str:
    # Same as models/warehouse_vendor.py
    if vendor_no < 900:
        return f"{vendor_no:03d}"
    nines, value = divmod(vendor_no - 900, 900)
    return "9" * (nines + 1) + f"{value:03d}"


STATEMENTS = [
    "ALTER TABLE warehouse_vendors ADD COLUMN IF NOT EXISTS vendor_no INTEGER NULL;",
    "ALTER TABLE warehouse_vendors ADD COLUMN IF NOT EXISTS vendor_code VARCHAR(10) NULL;",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_warehouse_vendors_vendor_no ON warehouse_vendors (vendor_no);",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_warehouse_vendors_vendor_code ON warehouse_vendors (vendor_code);",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_warehouse_vendors_name ON warehouse_vendors (lower(trim(name)));",
    """
    CREATE TABLE IF NOT EXISTS batches (
        id UUID PRIMARY KEY,
        location VARCHAR(20) NOT NULL DEFAULT 'warehouse',
        warehouse_vendor_id UUID NOT NULL REFERENCES warehouse_vendors(id),
        batch_no INTEGER NOT NULL,
        batch_date DATE NOT NULL,
        invoice_total NUMERIC(14, 2) NOT NULL,
        freight NUMERIC(12, 2) NOT NULL DEFAULT 0,
        cartage NUMERIC(12, 2) NOT NULL DEFAULT 0,
        markup_pct NUMERIC(6, 2) NOT NULL DEFAULT 0,
        status VARCHAR(10) NOT NULL DEFAULT 'OPEN',
        note VARCHAR(500) NULL,
        created_by UUID NOT NULL REFERENCES users(id),
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        closed_by UUID NULL REFERENCES users(id),
        closed_at TIMESTAMP NULL,
        CONSTRAINT ux_batches_vendor_batch_no UNIQUE (warehouse_vendor_id, batch_no)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_batches_location ON batches (location);",
    "CREATE INDEX IF NOT EXISTS ix_batches_warehouse_vendor_id ON batches (warehouse_vendor_id);",
    "CREATE INDEX IF NOT EXISTS ix_batches_status ON batches (status);",
    "CREATE INDEX IF NOT EXISTS ix_batches_created_at ON batches (created_at);",
    """
    CREATE TABLE IF NOT EXISTS batch_images (
        id UUID PRIMARY KEY,
        batch_id UUID NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
        file_url VARCHAR(500) NOT NULL,
        public_id VARCHAR(255) NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_batch_images_batch_id ON batch_images (batch_id);",
    # Phase 2: one product inside one batch, with its own barcode / cost / price / stock
    """
    CREATE TABLE IF NOT EXISTS product_batches (
        id UUID PRIMARY KEY,
        product_id UUID NOT NULL REFERENCES products(id),
        batch_id UUID NOT NULL REFERENCES batches(id),
        barcode VARCHAR(50) NOT NULL UNIQUE,
        cost NUMERIC(10, 2) NOT NULL,
        landed_cost NUMERIC(12, 2) NOT NULL,
        selling_price NUMERIC(10, 2) NOT NULL,
        warehouse_stock INTEGER NOT NULL DEFAULT 0,
        stock_level INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        CONSTRAINT ux_product_batches_product_batch UNIQUE (product_id, batch_id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_product_batches_product_id ON product_batches (product_id);",
    "CREATE INDEX IF NOT EXISTS ix_product_batches_batch_id ON product_batches (batch_id);",
    "ALTER TABLE stock_entries ADD COLUMN IF NOT EXISTS product_batch_id UUID NULL REFERENCES product_batches(id);",
    "CREATE INDEX IF NOT EXISTS ix_stock_entries_product_batch_id ON stock_entries (product_batch_id);",
    # Warehouse invoice: a batch moves to the shop with its own shop cost / price; in
    # another branch's DB the batch line is a copy with no batches row (batch_id NULL)
    "ALTER TABLE product_batches ALTER COLUMN batch_id DROP NOT NULL;",
    "ALTER TABLE product_batches ADD COLUMN IF NOT EXISTS label VARCHAR(100) NULL;",
    "ALTER TABLE product_batches ADD COLUMN IF NOT EXISTS shop_cost NUMERIC(10, 2) NULL;",
    "ALTER TABLE product_batches ADD COLUMN IF NOT EXISTS shop_price NUMERIC(10, 2) NULL;",
]


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        dups = await conn.fetch("""
            SELECT lower(trim(name)) AS n, count(*) FROM warehouse_vendors
            GROUP BY 1 HAVING count(*) > 1
        """)
        if dups:
            print(f"[{env}] STOPPED - repeated vendor names, fix them first: {[d['n'] for d in dups]}")
            return
        async with conn.transaction():
            await conn.execute(STATEMENTS[0])
            await conn.execute(STATEMENTS[1])
            # Number vendors that have none yet, oldest first, after the highest number used
            next_no = (await conn.fetchval("SELECT max(vendor_no) FROM warehouse_vendors") or 0) + 1
            rows = await conn.fetch("SELECT id, name FROM warehouse_vendors WHERE vendor_no IS NULL ORDER BY created_at, name")
            for row in rows:
                await conn.execute(
                    "UPDATE warehouse_vendors SET vendor_no = $1, vendor_code = $2 WHERE id = $3",
                    next_no, vendor_code_for(next_no), row["id"],
                )
                print(f"[{env}]   {vendor_code_for(next_no)}  {row['name'].strip()}")
                next_no += 1
            for sql in STATEMENTS[2:]:
                await conn.execute(sql)
        print(f"[{env}] vendor codes + batches + batch_images + product_batches ready")
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
