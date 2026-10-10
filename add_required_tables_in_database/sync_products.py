#!/usr/bin/env python3
"""
One-time product sync Light House -> Karim Abad.

Every Light House shop product that Karim Abad doesn't have (matched by barcode) is
created there with the same barcode / SKU / name / price and stock 0. Products Karim
Abad already has are not touched. Skipped: warehouse products (they reach Karim Abad
by warehouse transfer) and "(dummy)" display pieces.

New products are copied by the Add Product API from now on (services/product_mirror.py).

    python add_required_tables_in_database/sync_products.py --dry-run   # counts only
    python add_required_tables_in_database/sync_products.py

Idempotent: a second run copies nothing.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

import asyncpg
from dotenv import load_dotenv

load_dotenv()

SRC_ENV, DST_ENV = "DATABASE_URL", "DATABASE_URL_KARIMABAD"
DST_BRANCH = "European Sports Karim Abad"
COPY = ("sku", "name", "unit_price", "cost_price", "attributes", "barcode", "discount",
        "category", "limited_qty", "brand_action", "article_no")


def connect(env):
    return asyncpg.connect(os.environ[env].replace("postgresql+asyncpg://", "postgresql://", 1))


async def main(dry_run: bool):
    src, dst = await connect(SRC_ENV), await connect(DST_ENV)
    try:
        rows = await src.fetch(f"""
            SELECT id, {', '.join(COPY)} FROM products
            WHERE NOT is_warehouse_product AND name NOT ILIKE '%dummy%'
              AND barcode IS NOT NULL AND barcode <> ''
            ORDER BY created_at
        """)
        have = await dst.fetch("SELECT id, sku, lower(name) AS name, barcode FROM products")
        barcodes = {r["barcode"] for r in have}
        skus = {r["sku"] for r in have}
        names = {r["name"] for r in have}
        ids = {r["id"] for r in have}

        to_copy, clashes = [], []
        for r in rows:
            if r["barcode"] in barcodes:
                continue
            if r["sku"] in skus or r["name"].lower() in names:
                clashes.append(r)
                continue
            to_copy.append(r)
            skus.add(r["sku"]); names.add(r["name"].lower()); barcodes.add(r["barcode"])

        print(f"Light House shop products: {len(rows)} | already in Karim Abad: {len(rows) - len(to_copy) - len(clashes)}"
              f" | to copy: {len(to_copy)} | skipped (name/SKU taken with another barcode): {len(clashes)}")
        for r in clashes:
            print(f"   skipped: {r['name']} [{r['sku']}] barcode {r['barcode']}")
        if dry_run or not to_copy:
            print("Dry run - nothing written." if dry_run else "Nothing to copy.")
            return

        now = datetime.now()
        records = [
            (r["id"] if r["id"] not in ids else uuid.uuid4(), *[r[c] for c in COPY], DST_BRANCH, now)
            for r in to_copy
        ]
        cols = ("id",) + COPY + ("branch", "created_at")
        placeholders = ", ".join(f"${i}" for i in range(1, len(cols) + 1))
        async with dst.transaction():
            await dst.executemany(f"""
                INSERT INTO products ({', '.join(cols)}, updated_at, stock_level, is_warehouse_product,
                                      warehouse_stock, warehouse_cost, warehouse_limited_qty)
                VALUES ({placeholders}, ${len(cols)}, 0, FALSE, 0, 0, 0)
            """, records)
        print(f"Copied {len(records)} products to Karim Abad (stock 0).")
    finally:
        await src.close()
        await dst.close()


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
