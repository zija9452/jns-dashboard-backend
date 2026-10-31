# Warehouse -> Light House / Karimabad invoices for the B-2 issue stock (Category Wise + Issue 31-10-2026.xlsx).
# Calls the software's own create_warehouse_invoice, so stock, Stock In entries, WIN number, branch transfer
# and customer balance happen exactly as from the Warehouse Invoice page.
#   python issue_invoices.py --dry-run
#   python issue_invoices.py LH      (then KA)
import asyncio, base64, os, sys
from collections import OrderedDict
from types import SimpleNamespace

os.chdir(r"D:\EuropeanSports\backend")
sys.path.insert(0, r"D:\EuropeanSports\backend")
import openpyxl
from sqlalchemy import select, func
from src.database.database import session_factories
from src.models.product import Product
from src.models.user import User
from src.models.role import Role
from src.models.warehouse_customer import WarehouseCustomer
from src.routers.warehouse_invoice import create_warehouse_invoice

DIR = r"D:\EuropeanSports\Software Excel Reports\warehouse vendors-Stock 21-10-2026 b-2"
XLSX = DIR + r"\Warehouse Stock B-2 Category Wise + Issue 31-10-2026.xlsx"
CUSTOMERS = {"LH": ("European Sports Light House", 12), "KA": ("European Sports Karimabad", 13)}  # issue column index


def issue_rows(col):
    """barcode -> [qty, category] in file order; Transparent Dice's 2 rows add up."""
    out = OrderedDict()
    ws = openpyxl.load_workbook(XLSX)["Category Wise"]
    for r in ws.iter_rows(min_row=3, values_only=True):
        if isinstance(r[0], int) and r[col]:
            out.setdefault(r[16], [0, r[2]])[0] += r[col]
    return out


async def main(which, dry):
    async with session_factories["lighthouse"]() as db:
        admin = (await db.execute(select(User).join(Role, User.role_id == Role.id).where(Role.name == "admin").limit(1))).scalar_one()
        for code in which:
            cname, col = CUSTOMERS[code]
            cust = (await db.execute(select(WarehouseCustomer).where(WarehouseCustomer.name == cname))).scalar_one()
            items, total, problems = [], 0, []
            for bc, (qty, cat) in issue_rows(col).items():
                p = (await db.execute(select(Product).where(Product.barcode == bc, Product.is_warehouse_product))).scalar_one()
                same = (await db.execute(select(func.count()).where(Product.name == p.name))).scalar()
                if same != 1:
                    problems.append(f"name not unique: {p.name}")
                if (p.warehouse_stock or 0) < qty:
                    problems.append(f"stock {p.name}: {p.warehouse_stock} < {qty}")
                items.append({"pro_name": p.name, "pro_quantity": qty, "unit_price": float(p.cost_price),
                              "shop_price": float(p.unit_price), "discount": 0, "cat_name": cat})
                total += qty * p.cost_price
            print(f"{code} {cname}: {len(items)} items, qty {sum(i['pro_quantity'] for i in items)}, total {total}, "
                  f"balance {cust.cus_balance} -> {cust.cus_balance + total}")
            print("   problems:", problems or "none")
            if dry or problems:
                continue
            res = await create_warehouse_invoice(
                {"items": items, "customer_id": str(cust.id), "payment_method": "credit",
                 "payment_date": "2026-10-31T00:00:00", "amount_paid": 0, "manual_discount": 0,
                 "notes": "B-2 issue stock 31-10-2026"},
                current_user=SimpleNamespace(id=admin.id), db=db)
            print("   ", res["invoice_no"], "transfer:", res["transfer_status"], res["transfer_error"])
            pdf = res.get("pdf")
            if pdf:
                path = DIR + rf"\{res['invoice_no']} {cname} B-2 Issue 31-10-2026.pdf"
                with open(path, "wb") as f:
                    f.write(base64.b64decode(pdf.split(",")[-1]) if isinstance(pdf, str) else pdf)
                print("    PDF:", path)


args = [a for a in sys.argv[1:] if a in CUSTOMERS]
asyncio.run(main(args or list(CUSTOMERS), "--dry-run" in sys.argv))
