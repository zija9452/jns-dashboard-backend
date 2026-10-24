#!/usr/bin/env python3
"""
Import of the Sadaqat Sports warehouse products (sheet "INV-627" of
"Software Excel Reports/warehouse vendor b-2/Sadaqat Sports Vendor.xlsx").
Same rules as add_jaleel_products.py; vendor "Sadaqat Sports" is created if missing.
Rows without a Final selling price are skipped (not priced yet).

    python add_required_tables_in_database/add_sadaqat_products.py --dry-run   # list only
    python add_required_tables_in_database/add_sadaqat_products.py
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

XLSX = r"D:\EuropeanSports\Software Excel Reports\warehouse vendor b-2\Sadaqat Sports Vendor.xlsx"
SKIP = set()
SUFFIX = " B-2"
VENDOR = "Sadaqat Sports"
LH, KA = "European Sports Light House", "European Sports Karim Abad"
LH_PREFIX = "690"
REF = f"W_IN_{datetime.now():%Y%m%d}"
SHOP_LIMITED_QTY = 5  # both shops; warehouse limited qty = half of Qty (rounded down)

# No brand in the names -> vendor name
BRANDS = {"BALL DUNLOP": "Dunlop", "BALL ES": "ES", "TJD PUMP": "TJD", "TT RACKET LOKI 3000": "Loki", "TT BALL BUTTERFLY": "Butterfly", "BASKET BALL MOLTEN": "Molten", "Hashim Shuttle Cock": "Hashim", "NIKAR UX": "UX", "PADEL BABOLAT": "Babolat", "PADEL ADIDAS": "Adidas", "Swimming Arena Ialy GLASSES": "Arena",
          "Swimming Sailto GLASSES": "Sailto"}
CATEGORY = {"WHISTLE STEEL 10PCS": "Football Accessories", "WHISTLE FOX": "Football Accessories",
            "LUDO LASANI with Jar M": "Indoor Games", "LUDO LASANI with Jar L": "Indoor Games",
            "Ludo Jar X Big": "Indoor Games", "DICE WHITE": "Indoor Games", "Transparent Dice": "Indoor Games",
            "WHISTLE TENGMA": "Football Accessories", "YOGA MAT": "Fitness Accessories",
            "FOAM BALL L": "Indoor Games", "FOAM BALL M": "Indoor Games", "FOOTBALL Small": "FOOTBALL",
            "CARPET LUDO L": "Indoor Games", "Magnetic Chess": "Indoor Games", "CHESS 3IN1": "Indoor Games",
            "Magnetic Ludo": "Indoor Games", "FLAG SET": "Football Accessories",
            "DART BOARD MAGNET S": "Indoor Games", "DART MAGNET L": "Indoor Games", "DART BOARD MAGNET L": "Indoor Games",
            "Boili DART BOARD MAGNET S": "Indoor Games", "Target Bull's Eye Game DART MAGNET": "Indoor Games",
            "Boili DART BOARD MAGNET L": "Indoor Games",
            "HAND GRIP GP": "Fitness Accessories", "HAND GRIP METER with Box": "Fitness Accessories",
            "BAT Protective SHEET": "Cricket Accessories", "WICKET SPRING": "Cricket Accessories",
            "GLOVES FOOTBALL": "FOOTBALL GLOVES", "RACKET JSL": "Badminton Accessories",
            "RACKET M59": "Badminton Accessories", "RACKET JALI": "Badminton Accessories",
            "RACKET BJ": "Badminton Accessories", "LAWN TENNIS RACKET": "Tennis Accessories",
            "Skating Board M": "Skating Accessories", "Skating Board L": "Skating Accessories", "Skating Board S": "Skating Accessories",
            "SOCKS NB": "Football Accessories", "BALL DUNLOP": "Cricket Hard Ball",
            "TT BALL": "Tennis Accessories", "PADEL BABOLAT": "Tennis Accessories",
            "PADEL ADIDAS": "Tennis Accessories", "PADEL": "Tennis Accessories",
            "Swimming Arena Ialy GLASSES": "Swimming Accessories", "Swimming Sailto GLASSES": "Swimming Accessories",
            "Swimming Nose and Ear Clip": "Swimming Accessories", "Swimming MOUTH GUARD": "Swimming Accessories",
            "CAPTAIN BAND": "Football Accessories", "Swimming CAP": "Swimming Accessories",
            "NIKAR UX": "Swimming Accessories",
            "BODY SHAPER CHINA": "Fitness Accessories",
            "Hashim Shuttle Cock": "Badminton Accessories",
            "TUMMY Trimmer": "Fitness Accessories",
            "Football Card Fifa": "Football Accessories",
            "Jumping ROPE STEEL": "Fitness Accessories",
            "BASKET BALL S": "BASKETBALL", "BASKET BALL L": "BASKETBALL", "BASKET BALL MOLTEN": "BASKETBALL",
            "TT BALL BUTTERFLY": "Tennis Accessories",
            "TT RACKET LOKI 3000": "Tennis Accessories",
            "HAND GRIP ADJ": "Fitness Accessories",
            "YOGA ROLLER S": "Yoga Accessories", "YOGA ROLLER L": "Yoga Accessories",
            "REFREE FLAG": "Football Accessories",
            "Waist Trimmer BELT": "Fitness Accessories",
            "Basketball RING": "BASKETBALL",
            "NAN CHAKU FOAM": "Martial Arts",
            "TJD PUMP": "Football Accessories",
            "KNOCKER with Stick": "Cricket Accessories",
            "BALL ES": "Cricket Accessories"}
RENAME = {"WHISTLE STEEL 10PCS": "Whistle Steel 10PCS", "WHISTLE FOX": "Whistle Fox",
          "LUDO LASANI with Jar M": "Ludo Lasani With Jar M", "LUDO LASANI with Jar L": "Ludo Lasani With Jar L",
          "DICE WHITE": "Dice White", "WHISTLE TENGMA": "Whistle Tengma",
          "YOGA MAT": "Yoga Mat", "FOAM BALL L": "Foam Ball L", "FOAM BALL M": "Foam Ball M",
          "FOOTBALL Small": "Football Small", "CARPET LUDO L": "Carpet Ludo L",
          "CHESS 3IN1": "Chess 3IN1", "FLAG SET": "Flag Set",
          "DART BOARD MAGNET S": "Dart Board Magnet S", "DART MAGNET L": "Dart Magnet L",
          "DART BOARD MAGNET L": "Dart Board Magnet L",
          "Boili DART BOARD MAGNET S": "Boili Dart Board Magnet S",
          "Target Bull's Eye Game DART MAGNET": "Target Bull's Eye Game Dart Magnet",
          "Boili DART BOARD MAGNET L": "Boili Dart Board Magnet L",
          "HAND GRIP GP": "Hand Grip GP", "HAND GRIP METER with Box": "Hand Grip Meter With Box",
          "HAND GRIP METER": "Hand Grip Meter With Box",  # Excel name changed back after add
          "BAT Protective SHEET": "Bat Protective Sheet", "WICKET SPRING": "Wicket Spring",
          "GLOVES FOOTBALL": "Gloves Football", "RACKET JSL": "Racket JSL",
          "RACKET M59": "Racket M59", "RACKET JALI": "Racket Jali",
          "RACKET BJ": "Racket BJ", "LAWN TENNIS RACKET": "Lawn Tennis Racket",
          "SOCKS NB": "Socks NB", "BALL DUNLOP": "Ball Dunlop",
          "TT BALL": "TT Ball", "PADEL BABOLAT": "Padel Babolat",
          "PADEL ADIDAS": "Padel Adidas", "PADEL": "Padel",
          "Swimming Arena Ialy GLASSES": "Swimming Arena Italy Glasses",
          "Swimming Sailto GLASSES": "Swimming Sailto Glasses",
          "Swimming Nose and Ear Clip": "Swimming Nose And Ear Clip",
          "Swimming MOUTH GUARD": "Swimming Mouth Guard", "CAPTAIN BAND": "Captain Band",
          "Swimming CAP": "Swimming Cap", "NIKAR UX": "Nikar UX",
          "BODY SHAPER CHINA": "Body Shaper China",
          "Hashim Shuttle Cock": "Hashim Shuttle Cock",
          "TUMMY Trimmer": "Tummy Trimmer",
          "Football Card Fifa": "Football Card Fifa",
          "Jumping ROPE STEEL": "Jumping Rope Steel",
          "BASKET BALL S": "Basket Ball S", "BASKET BALL L": "Basket Ball L", "BASKET BALL MOLTEN": "Basket Ball Molten",
          "TT BALL BUTTERFLY": "TT Ball Butterfly",
          "TT RACKET LOKI 3000": "TT Racket Loki 3000",
          "HAND GRIP ADJ": "Hand Grip ADJ",
          "YOGA ROLLER S": "Yoga Roller S", "YOGA ROLLER L": "Yoga Roller L",
          "REFREE FLAG": "Referee Flag",
          "Waist Trimmer BELT": "Waist Trimmer Belt",
          "Basketball RING": "Basketball Ring",
          "NAN CHAKU FOAM": "Nan Chaku Foam",
          "TJD PUMP": "TJD Pump",
          "KNOCKER with Stick": "Knocker With Stick",
          "BALL ES": "Ball ES"}
# Stock different from the Excel Qty (user count)
QTY = {"BALL ES": 119}


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
    # Row 1 header, data from row 2
    # columns: #, Vendor, Product Description, Qty, Price (cost), Freight, Local Cartage, 45%, Selling Price, Final selling price
    ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[0]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        name = (r[2] or "").strip()
        if not name or name.lower() in SKIP or not r[9]:
            continue
        rows.append({
            "excel_name": name,
            "name": title_case(RENAME.get(name, name)) + SUFFIX,
            "qty": QTY.get(name, qty(r[3])),
            "wh_limited": QTY.get(name, qty(r[3])) // 2,
            "category": CATEGORY.get(name, ""),
            "brand": BRANDS.get(name, VENDOR),
            "cost": Decimal(str(r[4] or 0)),
            "price": Decimal(str(r[9] or 0)),
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
        no_cat = [r["name"] for r in new if not r["category"].strip()]
        if no_cat and not dry_run:
            sys.exit(f"Stopped - no category for: {no_cat}. Add them to CATEGORY first.")
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
