# Pending Tasks

## 1. Quotation feature — DONE
Fully implemented: `models/quotation.py`, `routers/quotation.py` (create/list/get/update/
status/convert/pdf/delete), migration `add_quotations_table.py`, registered in `main.py`.
Frontend: `app/(invoices)/quotation/page.tsx` (builder), `app/(pages)/view-quotation/page.tsx`
(list). Sidebar link (Logout ke upar, Admin+Cashier only, new tab). Rush is derived from
`required_by_date` vs `rush_pricing_settings` (never a manual toggle), snapshotted per-row.
Customer + Team Name are now **required** on Quotation (same as Customer Invoice) - the
customer-less test rows this exposed were deleted; `convert_quotation_to_order` also now
has a safety-net 400 if `customer_id` is ever null, and carries the rush/deadline fields
over onto the created CustomerInvoice (see item 3).
Discount: overall (not per-item) discount field wired end-to-end (create/update payload,
totals card in builder, column in list) but the input is currently **commented out** in
`quotation/page.tsx` (search "Discount UI hidden for now") - re-enable by uncommenting
when discount is wanted again.
After creating a quotation, the PDF opens in-page in a modal (same pattern as
`view-quotation`/`duplicate-bill`) instead of redirecting to `/view-quotation`.
Not built: a dedicated `view-quotation/[id]/page.tsx` detail page, and no "Edit" UI for an
existing quotation (backend `PUT /quotation/{id}` supports items/dates/discount/notes, but
not customer/team - no frontend button calls it yet).

**Quotation only** reads T-shirt, Short, Trouser, Jacket, Hoodie Jacket, and Sando pricing
from local override files - `lib/localTshirtPricing.ts` (search "LOCAL_TSHIRT_PRICING"),
`lib/localShortPricing.ts` (search "LOCAL_SHORT_PRICING"),
`lib/localTrouserPricing.ts` (search "LOCAL_TROUSER_PRICING"),
`lib/localJacketPricing.ts` (search "LOCAL_JACKET_PRICING"),
`lib/localHoodieJacketPricing.ts` (search "LOCAL_HOODIE_JACKET_PRICING"), and
`lib/localSandoPricing.ts` (search "LOCAL_SANDO_PRICING") - instead of the DB. This was
deliberate so Quotation testing wouldn't depend on real `ideal_prices`/`price_modifiers`
rows being correct. Customer Invoice has no such fallback - it always reads these
categories' pricing straight from the DB (see item 2).

Bulk (5+) rate is set equal to the 1-piece rate in all four local override files - no bulk
discount has been defined for any category yet.

Trouser's base dimension in the DB is the sub-category "Pocket with zip" (Yes/No, both
850/piece), with modifiers Bottom Rib (Yes +70/No 0), Pipin (Yes +50/No 0), Fabric
(Dye Fabric 0 / Light Mesh -150 / Speedo 200gsm +200), and Size Type (Adult 0 / Youth -100
/ Oversize +300 / Oversize+ x2).

Jacket's base dimension in the DB was changed (by the user, directly via the admin UI) from
the old plain Zip/Rib/Pocket/Fabric/Size-Type combination table to Fabric being the sole
base (is_modifier: false) dimension with 3 options: "Dye Light Speedo" (1600/piece),
"Light Speedo" (2050/piece), "Speedo 280gsm" (2150/piece). Zip, Rib, Pocket are now
modifiers but contribute 0 either way (price doesn't change with these); Size Type is
Adult 0 / Youth 0 (no youth discount for Jacket, unlike other categories) / Oversize +300 /
Oversize+ x2.

Hoodie Jacket's base dimension was changed the same way as Jacket (Fabric-only base:
"Dye Light Speedo" 1610/piece, "Light Speedo" 2800/piece, "Speedo 280gsm" 3200/piece), plus
it additionally has a Pipin modifier (Yes +100/No 0) that Jacket doesn't have. Zip/Rib/
Pocket contribute 0 either way (same as Jacket); Size Type is Adult 0/Youth 0/Oversize +300/
Oversize+ x2 (same as Jacket).

Sando's base dimension was also changed to Fabric-only base (Polyzone 130gsm/Polyzone
160gsm/Light Mesh/Dye Fabric), with Rib and Size Type as modifiers - but **incomplete**:
only Polyzone 130gsm (750/piece) and Light Mesh (800/piece) prices were given, plus Rib=No
(baseline 0) and Size Type=Adult (baseline 0) and the usual Oversize +300/Oversize+ x2.
Still pending from the user: Polyzone 160gsm price, Dye Fabric price, Rib=Yes adjustment,
Youth adjustment - these are omitted from `LOCAL_SANDO_IDEAL_PRICES`/`LOCAL_SANDO_MODIFIERS`
(not defaulted to 0) and left blank in the Excel sheet so they don't silently under-price;
selecting those options just won't auto-fill a Rate until given.

For Trouser, Jacket, Hoodie Jacket, and Sando, the sub-category names/options were set up
directly in the DB (via the customer-category admin UI) before the local override numbers
were added - always re-check `customer_categories` in the DB for the current sub_category/
option spelling before writing or editing a local override file, since it must match
exactly. `Ideal_Price_Costing_Sheet_v2.xlsx`'s Trouser, Jacket, Hoodie Jacket, and Sando
sheets were all rebuilt from the old full-combination table into this base+modifier layout
(like T-shirt/Short).

## 2. Ideal Prices — re-enter later (DB cleared again, on purpose)
`ideal_prices` AND `price_modifiers` were both fully populated for T-shirt during this
round of testing (and confirmed correct), then **deliberately cleared back to 0 rows**
per explicit instruction. Confirmed impact: **Quotation is unaffected** (reads the local
file regardless, see item 1); **Customer Invoice now has no auto-filled Rate for T-shirt**
until these are re-entered - staff must type the Rate manually for T-shirt items there in
the meantime (confirmed acceptable for now, not a bug).
When ready to make it real, re-enter via `/ideal-pricing` (T-shirt category) these exact
numbers (already correct and tested once):
- Base dimension: **Neck Style** (8 options) - Round Neck/V-Neck = 950, Polo/V-Neck Polo/
  Sherwani Collar/V-Neck Sherwani Collar/Bent Neck = 1000, Indian Neck = 1100 (qty 1 and
  qty 5+ tiers are the same number - no bulk discount defined yet).
- Modifiers (check "Price Modifier" checkbox on each in Customer Category admin first -
  see the is_modifier/is_optional note below):
  - Sleeves: Half = 0, Full = +50
  - Fabric: Polyzone 130gsm = 0, Polyzone 160gsm = +100, Light Mesh = +100, Dye Fabric = -300
  - Size Type: Adult = 0, Youth = -50, Oversize = +300, Oversize+ = x2
  - **Rib** (new, optional field): Yes = +70, No = 0
  - **Zip** (new, optional field): Yes = +100, No = 0
- Formula: `final = (base_price + sum of flat modifiers) x product of multiply modifiers`.
- Other 2 categories (Caps, FLAG) are still plain manual combination pricing (no modifiers)
  - fill via `/ideal-pricing` page as before. Short, Trouser, Jacket, Hoodie Jacket, and
  Sando also use the base+modifier pattern now (see item 1) but their `ideal_prices`/
  `price_modifiers` DB rows are still empty - only the Quotation-only local override files
  have real numbers so far, and Sando's is still incomplete (see item 1).
- `E:\EuropeanSports\Ideal_Price_Costing_Sheet_v2.xlsx` has the fillable sheet (per-category,
  bordered, blank price columns) for getting real numbers from HR.

### Bug fixed along the way - is_modifier / is_optional flags were not persisting
`models/customer_category.py`'s `SubCategorySchema` (used for Create/Update validation) and
the Customer Category admin form (`app/(pages)/customer-category/page.tsx`) didn't carry
`is_modifier`/`is_optional` at all - any edit through that page silently wiped these flags
from every sub-category (this is what happened to T-shirt's Sleeves/Fabric/Size Type when
Rib was added/removed). Fixed: both fields added to the backend schema, the `/grouped` AND
the plain list (`GET /customer-category/`) endpoints now return them (two separate places
had the same bug), and the admin form has two checkboxes per sub-category ("Price
Modifier", "Optional") that persist correctly on create/edit now.

### Bug fixed - price_modifiers save failed with "invalid input value for enum adjustmenttype"
`models/price_modifier.py`'s `adjustment_type` column used `SAEnum(..., native_enum=True)`
(the default) even though the real DB column is plain VARCHAR - a stray Postgres enum type
named `adjustmenttype` existed (uppercase FLAT/MULTIPLY labels) from an earlier
`create_all()`, so any *new* modifier insert failed while older rows (saved before that
type existed) kept working. Fixed with `native_enum=False` on the column.

### Bug fixed - stale auto-filled Rate carried over when switching to an unpriced option
`quotation/page.tsx`'s Rate auto-fill `useEffect` only handled the case where
`matchedIdealPrice` resolves to a number (`setUnitPrice(matchedIdealPrice)`) - it never
handled the reverse case where a previously-matched combination changes to one with no
price defined (e.g. switching Fabric from Polyzone 130gsm, which has a price, to Polyzone
160gsm, which doesn't yet for Sando). The old auto-filled Rate just stayed in the field
even though the "No fixed price set for this combination — enter manually" warning was
correctly showing underneath it - visually contradictory and an easy way to accidentally
quote the wrong fabric at the wrong price. Fixed: the effect now clears the Rate (and
`priceWasAutoFilled`) when `matchedIdealPrice` goes back to null, but only if the current
value was itself auto-filled - a price staff typed in manually is left untouched.

## 3. Rush + Deadline on Customer Invoice — DONE
Implemented, mirroring Quotation: `models/customer_invoice.py` gained `required_by_date`,
`is_rush`, `rush_rate_snapshot`, `rush_threshold_snapshot`, `rush_charge` (migration
`add_customer_invoice_rush_deadline_columns.py`, already run). `routers/customer_invoice.py`'s
`save_customer_orders()` computes rush via a new `_compute_customer_invoice_rush()` helper
(mirrors `quotation.py`'s `_compute_rush`) and adds `rush_charge` into `net_amount`/
`total_amount` (discount stays informational-only - pre-existing quirk, untouched). The
`date = request_data.get('date')` shadowing gotcha was avoided with a `date_cls` alias.
Frontend (`customer-invoice/page.tsx`): "Deadline" field (label is just "Deadline", not
"Deadline (Required By)"), required, RUSH badge + live charge preview - rush settings are
fetched from the real `/api/rush-pricing/` endpoint (DB already has real values: 300/piece,
3-day threshold - no local override needed here, unlike T-shirt pricing).
Receipt PDF (`generate_simple_receipt_pdf`, shared by the normal receipt endpoint and
Duplicate Bill's customer-invoice branch) now shows a Deadline line, a "[RUSH ORDER]" tag,
and a separate "Rush Charge: +NNN" row instead of folding it silently into one number.
Duplicate Bill's 7-day Redis cache key was bumped to v5 so old cached PDFs regenerate.

## 4. Optional/collapsible category fields ("+" More Options) — DONE
New per-sub-category flag `is_optional` (alongside `is_modifier`, see item 2's bug note).
In both `quotation/page.tsx` and `customer-invoice/page.tsx`, sub-categories flagged
optional (currently: T-shirt's Rib, Zip) are hidden by default behind a "+ More options"
toggle instead of showing inline with the required fields - price calc and "required
field" validation both skip optional fields so an item can be added without touching them.

## 5. Still missing / not asked for yet
- No "Edit customer/team name" on an existing Quotation (see item 1).
- No way to bulk-fix old data through the UI - the is_modifier/is_optional restore +
  Rib/Zip add for T-shirt (item 2's bug note) was done via a direct one-off DB script this
  session, not through the (now-fixed) admin UI - fine as a one-time correction, but worth
  knowing if similar categories need the same fix later.
