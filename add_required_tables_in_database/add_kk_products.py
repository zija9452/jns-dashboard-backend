#!/usr/bin/env python3
"""
One-time import of the KK warehouse products (Sheet1 of Downloads/HsUnTQ.xlsx,
"Warehouse Stock 21-10-2026"). Same rules as add_jaleel_products.py:

Each row becomes a Light House warehouse product named "<Title Case name> B-2" with
warehouse stock = Quantity (stock-in from vendor KK, which adds Qty x Cost to his
balance like the Stock In page does), warehouse cost = Cost Price, shop price =
Final Sell Price, warehouse limited qty = half of Qty, shop limited qty 5.
Karim Abad gets the same product (same id / barcode / price) with stock 0.
Sheet categories that have an existing equivalent are mapped to it (CATEGORY_MAP).

    python add_required_tables_in_database/add_kk_products.py --dry-run   # list only
    python add_required_tables_in_database/add_kk_products.py

Idempotent: a product whose name already exists is skipped; vendor/category are
created only if missing.
"""
import asyncio
import json
import re
import sys
import time
import uuid
from datetime import datetime
from decimal import Decimal

import openpyxl

from add_jaleel_products import KA, LH, REF, SHOP_LIMITED_QTY, SUFFIX, connect, next_barcodes

XLSX = r"C:\Users\Administrator\Downloads\HsUnTQ.xlsx"
VENDOR = "KK"

CATEGORY_MAP = {
    "Badmintion": "Badminton Accessories",
    "Swimming": "Swimming Accessories",
    "Fitness wear": "Fitness Accessories",
    "Cricket Uniforms": "Cricket Kit",
}

# Words kept in capitals when an all-caps name is title-cased
KEEP_CAPS = {"AOPI"}

# Brand by sheet S.No; rows not listed -> KK
BRANDS = {
    1: "Wizal", 2: "Wizal", 40: "Wizal",
    3: "Adoral", 4: "Adoral", 5: "Adoral", 38: "Adoral", 41: "Adoral",
    9: "AOPI", 10: "AOPI",
    11: "Speedo", 12: "Speedo",
    15: "Advance", 16: "Sainteve",
    18: "TCL", 19: "TCL", 20: "TCL", 21: "TCL", 22: "TCL", 23: "TCL", 24: "TCL",
    25: "Gray-Nicolls", 28: "Hotik",
    31: "Blue Ocean", 32: "Blue Ocean", 33: "Blue Ocean", 34: "Blue Ocean", 39: "Blue Ocean",
    35: "Gripper", 36: "Gripper", 37: "Gripper",
}


def clean_name(text: str) -> str:
    """Title Case: first letter of every word (and of each '/' part) capitalised, the
    rest kept as written (CKT, F/S, 2Pc stay); an all-caps name is lowered first,
    except codes with digits (AP-2538, 2.5M) and KEEP_CAPS."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\(\s+", "(", text)
    all_caps = text == text.upper()
    words = []
    for w in text.split(" "):
        if all_caps and w not in KEEP_CAPS and not re.search(r"\d", w):
            w = w.lower()
        words.append("/".join(re.sub(r"^(\W*)(\w)", lambda m: m.group(1) + m.group(2).upper(), p) for p in w.split("/")))
    return " ".join(words)


def read_rows():
    ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[0]
    rows = []
    for r in ws.iter_rows(min_row=4, values_only=True):
        if not r[1]:
            continue
        qty = int(r[4] or 0)
        category = (r[2] or "").strip()
        rows.append({
            "sno": r[0],
            "name": clean_name(r[1]) + SUFFIX,
            "qty": qty,
            "wh_limited": qty // 2,
            "category": CATEGORY_MAP.get(category, category),
            "brand": BRANDS.get(r[0], VENDOR),
            "cost": Decimal(str(r[6] or 0)),
            "price": Decimal(str(r[11] or 0)),
        })
    return rows


async def main(dry_run: bool):
    rows = read_rows()
    lh, ka = await connect("DATABASE_URL"), await connect("DATABASE_URL_KARIMABAD")
    try:
        names = {db: {r["n"] for r in await db.fetch("SELECT lower(name) AS n FROM products")} for db in (lh, ka)}
        new = [r for r in rows if r["name"].lower() not in names[lh] and r["name"].lower() not in names[ka]]
        skipped = [r for r in rows if r not in new]
        barcodes = await next_barcodes(lh, ka, len(new))
        for r, b in zip(new, barcodes):
            r["barcode"] = b

        vendor_id = await lh.fetchval("SELECT id FROM warehouse_vendors WHERE lower(trim(name)) = lower($1)", VENDOR)
        categories = sorted({r["category"] for r in new})
        missing_cat = {db: [c for c in categories if not await db.fetchval("SELECT 1 FROM categories WHERE name = $1", c)]
                       for db in (lh, ka)}

        print(f"{'#':>3} {'Name':<60} {'Brand':<12} {'Category':<22} {'Qty':>4} {'WhLim':>5} {'Cost':>6} {'Price':>6}  Barcode")
        for r in new:
            print(f"{r['sno']:>3} {r['name']:<60} {r['brand']:<12} {r['category']:<22} {r['qty']:>4} {r['wh_limited']:>5} "
                  f"{r['cost']:>6} {r['price']:>6}  {r['barcode']}")
        balance = sum(r["qty"] * r["cost"] for r in new)
        print(f"\nShop limited qty (both branches): {SHOP_LIMITED_QTY}")
        print(f"To add: {len(new)} | already exist (skipped): {len(skipped)} | total qty: {sum(r['qty'] for r in new)}")
        for r in skipped:
            print(f"   skipped: {r['name']}")
        print(f"Vendor {VENDOR}: {'exists' if vendor_id else 'will be created'}; balance +{balance}")
        print(f"New categories - Light House: {missing_cat[lh] or 'none'} | Karim Abad: {missing_cat[ka] or 'none'}")
        if dry_run or not new:
            print("Dry run - nothing written." if dry_run else "Nothing to add.")
            return

        now = datetime.now()
        sku_base = int(time.time() * 1000)
        async with lh.transaction(), ka.transaction():
            if not vendor_id:
                vendor_id = uuid.uuid4()
                await lh.execute("""
                    INSERT INTO warehouse_vendors (id, name, contacts, branch, balance, payments_history, created_at, updated_at)
                    VALUES ($1, $2, $3, 'Warehouse Main', 0, '[]', $4, $4)
                """, vendor_id, VENDOR, json.dumps({"phone": "", "email": "", "address": ""}), now)
            for db, branch in ((lh, LH), (ka, KA)):
                for c in missing_cat[db]:
                    await db.execute("INSERT INTO categories (id, name, branch, created_at) VALUES ($1, $2, $3, $4)",
                                     uuid.uuid4(), c, branch, now)

            for i, r in enumerate(new):
                pid, sku = uuid.uuid4(), f"SKU-{sku_base + i}"
                common = (pid, sku, r["name"], r["price"], r["cost"], r["barcode"], r["category"], r["brand"], now)
                await lh.execute("""
                    INSERT INTO products (id, sku, name, unit_price, cost_price, barcode, category, brand_action,
                                          created_at, updated_at, branch, stock_level, discount, limited_qty,
                                          is_warehouse_product, warehouse_stock, warehouse_cost, warehouse_limited_qty)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9, $10, 0, 0, $11, TRUE, $12, $5, $13)
                """, *common, LH, SHOP_LIMITED_QTY, r["qty"], r["wh_limited"])
                await ka.execute("""
                    INSERT INTO products (id, sku, name, unit_price, cost_price, barcode, category, brand_action,
                                          created_at, updated_at, branch, stock_level, discount, limited_qty,
                                          is_warehouse_product, warehouse_stock, warehouse_cost, warehouse_limited_qty)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9, $10, 0, 0, $11, FALSE, 0, 0, 0)
                """, *common, KA, SHOP_LIMITED_QTY)
                if r["qty"] > 0:
                    await lh.execute("""
                        INSERT INTO stock_entries (id, product_id, warehouse_vendor_id, qty, cost_price, type, location, ref, created_at)
                        VALUES ($1, $2, $3, $4, $5, 'IN', 'warehouse', $6, $7)
                    """, uuid.uuid4(), pid, vendor_id, r["qty"], r["cost"], REF, now)
            await lh.execute("UPDATE warehouse_vendors SET balance = COALESCE(balance, 0) + $1, updated_at = $2 WHERE id = $3",
                             balance, now, vendor_id)
        print(f"Added {len(new)} products (Light House warehouse + Karim Abad shop, stock 0).")
    finally:
        await lh.close()
        await ka.close()


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
