# Pending Tasks

## 1. Quotation feature — DONE
Fully implemented: `models/quotation.py`, `routers/quotation.py` (create/list/get/update/
status/convert/pdf/delete), migration `add_quotations_table.py`, registered in `main.py`.
Frontend: `app/(invoices)/quotation/page.tsx` (builder), `app/(pages)/view-quotation/page.tsx`
(list). Sidebar link (Logout ke upar, Admin+Cashier only, new tab). Rush is derived from
`required_by_date` vs `rush_pricing_settings` (never a manual toggle), snapshotted per-row.
Not built: a dedicated `view-quotation/[id]/page.tsx` detail page — list page currently covers
view/PDF/status-change/convert, a separate detail view was never asked for.

## 2. Ideal Prices — re-enter tomorrow
`ideal_prices` table was cleared (0 rows) after testing. T-shirt's structure is ready to use:
- Base dimension: **Neck Style** (8 options: Round Neck, V-Neck, Polo, V-Neck Polo, Sherwani
  Collar, V-Neck Sherwani Collar, Bent Neck, Indian Neck) — needs a price per option again.
- Modifier dimensions (already configured in `price_modifiers`, untouched): Sleeves (Half=0,
  Full=+50), Size Type (Adult=0, Youth=-50, Oversize=+300, Oversize+=×2), Fabric (Polyzone
  130gsm=0, 160gsm=+100, Light Mesh=+100, Dye Fabric=-300).
- Formula: `final = (base_price + sum of flat modifiers) × product of multiply modifiers`.
- Other 7 categories (Jacket, Hoodie Jacket, Trouser, Short, Caps, FLAG, Sando) are still plain
  manual combination pricing (no modifiers) — fill via `/ideal-pricing` page as before.
- `E:\EuropeanSports\Ideal_Price_Costing_Sheet_v2.xlsx` has the fillable sheet (per-category,
  bordered, blank price columns) for getting real numbers from HR.

## 3. Rush + Deadline on Customer Invoice — NOT STARTED (reverted after a false start)
User wants the same rush/deadline mechanism Quotation has, added to the actual Customer Order
flow (`(invoices)/customer-invoice/page.tsx` + `models/customer_invoice.py` +
`routers/customer_invoice.py`'s `SaveCustomerOrders`), so orders directly created from Customer
Invoice (not via a quotation) also get `required_by_date` + auto `is_rush`/`rush_charge`.

Was briefly started and fully reverted (model fields, migration, router import all undone;
`customer_invoices` table is back to its original columns) because it was implemented before
being asked for — only this note was wanted at that point. Still fully pending.

### Implementation notes for when this is picked up
- Mirror `Quotation`'s fields on `CustomerInvoice`: `required_by_date`, `is_rush`,
  `rush_rate_snapshot`, `rush_threshold_snapshot`, `rush_charge`.
- **Gotcha already hit once**: inside `save_customer_orders()` in `routers/customer_invoice.py`,
  a local variable `date = request_data.get('date')` shadows the module-level `datetime.date`
  import for the rest of that function's scope. Any rush-date logic added inside that function
  must import `date` under an alias (e.g. `from datetime import date as date_cls`) rather than
  relying on the top-of-file import.
- `net_amount` in that function is currently `= total_amount` (discount is tracked in
  `total_discount` but never actually subtracted — a pre-existing quirk, not something to "fix"
  as part of this). Add rush the same way discount is currently handled informationally, but
  rush_charge **should** be added into `net_amount`/`total_amount` (unlike discount) since it's
  a real amount owed - reference how `quotation.py`'s `_compute_rush` + `_build_totals` do it.
- Frontend: add "Deadline (Required By)" field (decide mandatory or optional — Quotation makes
  it mandatory), fetch `/api/rush-pricing/` on mount, live-preview `is_rush`/`rush_charge` in the
  totals card the same way `(invoices)/quotation/page.tsx` does, include `required_by_date` in
  the `SaveCustomerOrders` payload.
- No "Rush Order?" checkbox anywhere — same derived-not-chosen rule as Quotation.
