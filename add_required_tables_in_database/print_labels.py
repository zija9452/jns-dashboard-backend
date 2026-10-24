#!/usr/bin/env python3
"""
Print shop-style barcode labels (barcode + name + "Rs. <price>") straight to the
Zebra printer, same ZPL as /stock/generatebarcodesonly. Only prints - no stock or
DB change. Names too long for one line (> 41 chars) are split at the space nearest
the middle and printed on 2 lines with a shorter barcode.

    python add_required_tables_in_database/print_labels.py "JK Cricket Batting Pad B-2=18" "SG Cricket Gloves B-2=6" --dry-run
    python add_required_tables_in_database/print_labels.py "JK Cricket Batting Pad B-2=18"

Each argument is "<exact product name>=<labels>"; price and barcode come from the
Light House DB. Needs pywin32 (requirements-host-print.txt).
"""
import asyncio
import os
import sys

import asyncpg
from dotenv import load_dotenv

load_dotenv()

PRINTER = "ZDesigner GX420d"
ONE_LINE_MAX = 41  # chars that fit in 400 dots at the min name font 16


def centered_barcode_x(data, module_width=2):
    # Same as routers/stock.py
    return max(int(208 - (11 * (len(data) + 2) + 13) * module_width / 2), 0)


def fitted_name_font_size(name, block_width=400, max_size=19, min_size=16):
    # Same as routers/stock.py
    return max(min_size, min(max_size, int(block_width / (len(name) * 0.6))))


def split_name(name):
    """Split at the space nearest the middle so both lines are about equal."""
    spaces = [i for i, ch in enumerate(name) if ch == " "]
    cut = min(spaces, key=lambda i: abs(i - len(name) / 2))
    return name[:cut], name[cut + 1:]


def label(name, barcode, price):
    price_zpl = f"^FO80,175^A0N,30,30^FB250,1,0,C^FDRs. {int(price)}^FS"
    x = centered_barcode_x(barcode)
    if len(name) <= ONE_LINE_MAX:
        f = fitted_name_font_size(name)
        return ("^XA" f"^FO{x},40^BY2,2,80^BCN,80,Y,N,N^FD{barcode}^FS"
                f"^FO10,150^A0N,{f},{f}^FB400,1,0,C^FD{name}^FS" + price_zpl + "^XZ")
    line1, line2 = split_name(name)
    return ("^XA" f"^FO{x},25^BY2,2,65^BCN,65,Y,N,N^FD{barcode}^FS"
            f"^FO10,122^A0N,19,19^FB400,1,0,C^FD{line1}^FS"
            f"^FO10,145^A0N,19,19^FB400,1,0,C^FD{line2}^FS" + price_zpl + "^XZ")


async def main(items, dry_run):
    c = await asyncpg.connect(os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1))
    jobs = []
    try:
        for name, n in items:
            p = await c.fetchrow("SELECT name, barcode, unit_price FROM products WHERE name = $1", name)
            if not p:
                sys.exit(f"Product not found: {name}")
            jobs.append((p, n))
    finally:
        await c.close()
    for p, n in jobs:
        lines = "2 lines" if len(p["name"]) > ONE_LINE_MAX else "1 line"
        print(f"{n:>4}  {p['barcode']}  Rs. {int(p['unit_price']):<5} {p['name']}  ({lines})")
    print(f"Total labels: {sum(n for _, n in jobs)}")
    if dry_run:
        print("Dry run - nothing printed.")
        return

    import win32print
    for p, n in jobs:
        h = win32print.OpenPrinter(PRINTER)
        try:
            win32print.StartDocPrinter(h, 1, (f"Labels {p['barcode']}", None, "RAW"))
            win32print.StartPagePrinter(h)
            win32print.WritePrinter(h, (label(p["name"], p["barcode"], p["unit_price"]) * n).encode("ascii"))
            win32print.EndPagePrinter(h)
            win32print.EndDocPrinter(h)
        finally:
            win32print.ClosePrinter(h)
    print(f"Sent {len(jobs)} jobs to {PRINTER}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if not args:
        sys.exit(__doc__)
    items = []
    for a in args:
        name, _, n = a.rpartition("=")
        items.append((name.strip(), int(n)))
    asyncio.run(main(items, "--dry-run" in sys.argv))
