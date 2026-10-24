#!/usr/bin/env python3
"""
One-time import of the Jaleel warehouse products (Sheet4 of
"Software Excel Reports/Warehouse new product stock.xlsx").

Each row becomes a Light House warehouse product named "<Title Case name> B-2" with
warehouse stock = Qty (stock-in from vendor Jaleel, which adds Qty x Cost to his
balance like the Stock In page does), warehouse cost = Cost Price and shop price =
Final selling price. Karim Abad gets the same product (same id / barcode / price)
as a shop product with stock 0, like services/product_mirror.py does.
"Cricket Bat" and "Cricket bat with cover" are skipped.

    python add_required_tables_in_database/add_jaleel_products.py --dry-run   # list only
    python add_required_tables_in_database/add_jaleel_products.py

Idempotent: a product whose name already exists is skipped; vendor/category are
created only if missing.
"""
import asyncio
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from decimal import Decimal

import asyncpg
import openpyxl
from dotenv import load_dotenv

load_dotenv()

XLSX = r"D:\EuropeanSports\Software Excel Reports\warehouse vendor b-2\Jaleel Vendor.xlsx"
SKIP = {"cricket bat", "cricket bat with cover"}
SUFFIX = " B-2"
VENDOR = "Jaleel"
LH, KA = "European Sports Light House", "European Sports Karim Abad"
LH_PREFIX = "690"
REF = f"W_IN_{datetime.now():%Y%m%d}"
SHOP_LIMITED_QTY = 5  # both shops; warehouse limited qty = half of Qty (rounded down)

# Brand by Excel product name (the sheet's Brand column holds numbers); unclear ones -> Jaleel
BRANDS = {
    "Gray Nicolls Cricket Batting Pad Red": "Gray Nicolls",
    "DSC Cricket Batting Pad": "DSC",
    "SS Cricket Batting Pad": "SS",
    "MRF Cricket Batting Pads": "MRF",
    "JK Cricket Batting Pad (blue)": "JK",
    "JK Cricket Batting Pad": "JK",
    "Spartan Cricket Batting Pad": "Spartan",
    "Gray Nicolls Cricket Batting Pad Blue": "Gray Nicolls",
    "Gray Nicolls Cricket Keeping Pads": "Gray Nicolls",
    "SS Cricket Batting Pad golden": "SS",
    "Wizal Cricket Batting Pad": "Wizal",
    "MA Cricket Batting Pad (shing pads king)": "MA",
    "SG Cricket Gloves": "SG",
    "SS Cricket Gloves": "SS",
    "NB Cricket Gloves": "NB",
    "DSC Keeper Cricket Gloves green": "DSC",
    "SG Keeper Cricket Gloves": "SG",
    "Moonwalker Cricket Thigh Guard L": "Moonwalker",
    "Javan Kingfisher Thigh Guard JK": "JK",
    "Cricket Helmet gray nicolls": "Gray Nicolls",
    "Shrey Cricket Helmet": "Shrey",
    "BK Arm Sleeve": "BK",
    "Gray Nicolls Arm Guard elbow": "Gray Nicolls",
    "Batting Gloves Normal": "Gray Nicolls",
    "Gray Nicolls Batting Gloves": "Gray Nicolls",
    "SG GLOVES FULL EYE": "SG",
    "(DSC) SG Keeping Gloves orange": "SG",
    "SS Keeper Cricket Gloves": "SS",
    "(SS) IMP Keeper Cricket Gloves": "SS",
}

# Category for rows whose Category cell is empty
CATEGORY = {"Gray Nicolls Batting Gloves": "Cricket Accessories", "SG GLOVES FULL EYE": "Cricket Accessories",
            "(DSC) SG Keeping Gloves orange": "Cricket Accessories",
            "SS Keeper Cricket Gloves": "Cricket Accessories",
            "(SS) IMP Keeper Cricket Gloves": "Cricket Accessories"}


# Excel name -> name used in the system (before Title Case / B-1)
RENAME = {"MA Cricket Batting Pad (shing pads king)": "MA Cricket Batting Pad",
          "SG GLOVES FULL EYE": "SG Gloves Full Eye",
          "(DSC) SG Keeping Gloves orange": "SG Keeping Gloves orange",
          "(SS) IMP Keeper Cricket Gloves": "IMP Keeper Cricket Gloves",
          "Beyond Fear Cricket Gloves (SG)": "Beyond Fear Cricket Gloves"}


def title_case(text: str) -> str:
    """'SS Cricket Batting Pad golden' -> 'SS Cricket Batting Pad Golden'
    (first letter of each word capitalised; all-caps words like SS / MRF stay)."""
    words = re.sub(r"\s+", " ", text).strip().split(" ")
    out = []
    for w in words:
        lead = len(w) - len(w.lstrip("("))
        core = w[lead:]
        if core and not core.isupper():
            core = core[0].upper() + core[1:].lower()
        out.append(w[:lead] + core)
    return " ".join(out)


def check_digit(code: str) -> int:
    # Same as ProductService.calculate_check_digit
    s = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(code))
    return (10 - s % 10) % 10


def connect(env):
    return asyncpg.connect(os.environ[env].replace("postgresql+asyncpg://", "postgresql://", 1))


def qty(cell) -> int:
    """Qty cell may carry a note after the number, e.g. "8 (newline) last count was 9"."""
    m = re.match(r"\s*(\d+)", str(cell or 0))
    return int(m.group(1)) if m else 0


def read_rows():
    ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[3]
    rows = []
    for r in ws.iter_rows(min_row=4, values_only=True):
        name = (r[2] or "").strip()
        if not name or name.lower() in SKIP:
            continue
        rows.append({
            "excel_name": name,
            "name": title_case(RENAME.get(name, name)) + SUFFIX,
            "qty": qty(r[3]),
            "wh_limited": qty(r[3]) // 2,
            "category": title_case(r[4] or CATEGORY.get(name, "")),
            "brand": BRANDS.get(name, VENDOR),
            "cost": Decimal(str(r[6] or 0)),
            "price": Decimal(str(r[11] or 0)),
        })
    return rows


async def next_barcodes(lh, ka, n):
    # Same sequence as ProductService.generate_unique_barcode (Light House prefix 690)
    last = await lh.fetchval("""
        SELECT barcode FROM products
        WHERE barcode LIKE $1 AND LENGTH(barcode) = 9 AND barcode ~ '^[0-9]{9}$'
          AND CAST(SUBSTRING(barcode FROM 4 FOR 5) AS INTEGER) < 10000
        ORDER BY barcode DESC LIMIT 1
    """, LH_PREFIX + "%")
    seq = int(last[3:-1]) + 1 if last else 0
    taken = {r["barcode"] for db in (lh, ka) for r in await db.fetch("SELECT barcode FROM products WHERE barcode IS NOT NULL")}
    out = []
    while len(out) < n:
        base = f"{LH_PREFIX}{seq:05d}"
        code = f"{base}{check_digit(base)}"
        if code not in taken:
            out.append(code)
        seq += 1
    return out


async def main(dry_run: bool):
    rows = read_rows()
    if "--only" in sys.argv:  # --only "Excel product name": add just that row
        only = sys.argv[sys.argv.index("--only") + 1].strip().lower()
        rows = [r for r in rows if r["excel_name"].lower() == only]
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

        print(f"{'Name':<50} {'Brand':<13} {'Category':<20} {'Qty':>4} {'WhLim':>5} {'Cost':>7} {'Price':>7}  Barcode")
        for r in new:
            print(f"{r['name']:<50} {r['brand']:<13} {r['category']:<20} {r['qty']:>4} {r['wh_limited']:>5} {r['cost']:>7} {r['price']:>7}  {r['barcode']}")
        print(f"Shop limited qty (both branches): {SHOP_LIMITED_QTY}")
        balance = sum(r["qty"] * r["cost"] for r in new)
        print(f"\nTo add: {len(new)} | already exist (skipped): {len(skipped)}")
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
