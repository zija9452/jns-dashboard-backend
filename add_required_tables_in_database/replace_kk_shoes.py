#!/usr/bin/env python3
"""
Replace the 9 KK shoe articles added on 2026-10-21 without sizes by the 50 sized
products of "Software Excel Reports/warehouse vendor b-2/KK Vendor.xlsx" (Sheet1, S.No 31-80).

Old products (both branches) and their Stock In entries are deleted and their value
taken off the KK balance; the sized products are then added like add_kk_products.py
(Light House warehouse stock = Qty, Karim Abad stock 0, Stock In from KK). The sizes
add up to the old stock, so the KK balance ends where it was.

    python add_required_tables_in_database/replace_kk_shoes.py --dry-run   # list only
    python add_required_tables_in_database/replace_kk_shoes.py
"""
import asyncio
import sys
import time
import uuid
from datetime import datetime
from decimal import Decimal

import openpyxl

from add_jaleel_products import KA, LH, REF, SHOP_LIMITED_QTY, SUFFIX, connect, next_barcodes
from add_kk_products import clean_name

XLSX = r"D:\EuropeanSports\Software Excel Reports\warehouse vendor b-2\KK Vendor.xlsx"
VENDOR = "KK"
SNO_FROM, SNO_TO = 31, 80

# Old size-less products (barcode) -> they are replaced by the sized rows
OLD_BARCODES = ["690004807", "690004814", "690004821", "690004838", "690004845",
                "690004852", "690004869", "690004876", "690004883"]


def brand(name: str) -> str:
    if "Gripper" in name:
        return "Gripper"
    if "Adoral" in name:
        return "Adoral"
    return "Blue Ocean"


def read_rows():
    ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[0]
    rows = []
    for r in ws.iter_rows(min_row=4, values_only=True):
        if not isinstance(r[0], int) or not SNO_FROM <= r[0] <= SNO_TO or not r[1]:
            continue
        excel = r[1].strip()
        if excel.upper().endswith(" B-2"):
            excel = excel[:-4]
        name = clean_name(excel) + SUFFIX
        qty = int(r[4] or 0)
        rows.append({
            "sno": r[0], "name": name, "qty": qty, "wh_limited": qty // 2,
            "category": (r[2] or "").strip(), "brand": brand(name),
            "cost": Decimal(str(r[6] or 0)), "price": Decimal(str(r[11] or 0)),
        })
    return rows


async def main(dry_run: bool):
    rows = read_rows()
    lh, ka = await connect("DATABASE_URL"), await connect("DATABASE_URL_KARIMABAD")
    try:
        old = await lh.fetch("SELECT id, name, barcode, warehouse_stock, warehouse_cost FROM products "
                             "WHERE barcode = ANY($1::text[]) ORDER BY barcode", OLD_BARCODES)
        old_ids = [o["id"] for o in old]
        old_entries = await lh.fetch("SELECT id, qty, cost_price FROM stock_entries WHERE product_id = ANY($1::uuid[])", old_ids)
        other_refs = await lh.fetchval("SELECT count(*) FROM stock_entries WHERE product_id = ANY($1::uuid[]) "
                                       "AND NOT (type::text = 'IN' AND location::text = 'warehouse')", old_ids)
        old_value = sum(e["qty"] * e["cost_price"] for e in old_entries)

        names = {r["n"] for db in (lh, ka) for r in await db.fetch("SELECT lower(name) AS n FROM products")}
        clash = [r["name"] for r in rows if r["name"].lower() in names]
        barcodes = await next_barcodes(lh, ka, len(rows))
        for r, b in zip(rows, barcodes):
            r["barcode"] = b
        new_value = sum(r["qty"] * r["cost"] for r in rows)
        vendor_id = await lh.fetchval("SELECT id FROM warehouse_vendors WHERE lower(trim(name)) = lower($1)", VENDOR)
        balance = await lh.fetchval("SELECT balance FROM warehouse_vendors WHERE id = $1", vendor_id)

        print("DELETE (Light House + Karim Abad):")
        for o in old:
            print(f"   {o['barcode']}  stock {o['warehouse_stock']:>3}  {o['name']}")
        print(f"   {len(old_entries)} stock entries, value {old_value}; other stock movements: {other_refs}")
        print(f"\nADD {len(rows)}:")
        print(f"{'S.No':>4} {'Name':<64} {'Brand':<11} {'Qty':>3} {'Lim':>3} {'Cost':>6} {'Price':>6}  Barcode")
        for r in rows:
            print(f"{r['sno']:>4} {r['name']:<64} {r['brand']:<11} {r['qty']:>3} {r['wh_limited']:>3} {r['cost']:>6} {r['price']:>6}  {r['barcode']}")
        print(f"\nOld stock {sum(o['warehouse_stock'] for o in old)} -> new {sum(r['qty'] for r in rows)}")
        print(f"KK balance {balance} - {old_value} + {new_value} = {balance - old_value + new_value}")
        if clash:
            print("Name already exists:", clash)
        if len(old) != 9 or other_refs or clash or not vendor_id:
            sys.exit("Stopped: check the lines above.")
        if dry_run:
            print("Dry run - nothing written.")
            return

        now = datetime.now()
        sku_base = int(time.time() * 1000)
        async with lh.transaction(), ka.transaction():
            await lh.execute("DELETE FROM stock_entries WHERE product_id = ANY($1::uuid[])", old_ids)
            for db in (lh, ka):
                n = await db.execute("DELETE FROM products WHERE id = ANY($1::uuid[])", old_ids)
                assert n == "DELETE 9", n
            for i, r in enumerate(rows):
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
                await lh.execute("""
                    INSERT INTO stock_entries (id, product_id, warehouse_vendor_id, qty, cost_price, type, location, ref, created_at)
                    VALUES ($1, $2, $3, $4, $5, 'IN', 'warehouse', $6, $7)
                """, uuid.uuid4(), pid, vendor_id, r["qty"], r["cost"], REF, now)
            await lh.execute("UPDATE warehouse_vendors SET balance = COALESCE(balance, 0) - $1 + $2, updated_at = $3 WHERE id = $4",
                             old_value, new_value, now, vendor_id)
        print(f"Deleted 9 old, added {len(rows)} sized products.")
    finally:
        await lh.close()
        await ka.close()


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
