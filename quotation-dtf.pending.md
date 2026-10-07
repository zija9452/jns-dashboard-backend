# Pending: DTF category in Quotation (auto layout + price by roll length)

Status: **Done (2026-10-02), as a different design** - DTF is not its own category. It is an
optional "DTF logos" box on Hoodie / Jacket lines (customer_categories.dtf_enabled), priced per
0.5 m of a 23" roll, rule on the Ideal Pricing page (dtf_pricing_settings), saved layout shown to
the designer on the Invoice Details page. Code: frontend lib/dtfLayout.ts, components/DtfLogos.tsx,
backend utils/dtf_charges.py, routers/dtf_pricing.py, migration add_dtf_logos.py. The rest of this
file is the original (superseded) proposal.

## 1. The problem

DTF is printed on a roll that is **23" wide**. We charge by the length of roll used:
**1 meter (39") = Rs 1,500**.

A customer can order many designs in one DTF job, each with its own width, height and qty.
The designs must share the roll:
- A 15" wide design leaves 23 - 15 - 0.5 = **7.5"** next to it. A second design wider than
  that cannot sit beside it, so it goes to the **next line** (lower on the roll).
- A small design (e.g. 3×3) can fit in that 7.5" gap, so it adds **no extra length**.
- There must be a **0.5" gap** between designs, horizontally and vertically.

The quotation page must show the customer the price **instantly** while they type sizes.

## 2. What the page does now

File: `frontend/dashboard/frontend/app/(invoices)/quotation/page.tsx`

- Every category works as: pick options (sub-categories) → quantity → rate → line total.
- Prices come from the DB (`/api/customer-category/grouped`) or from local test files
  (`lib/localTshirtPricing.ts`, `lib/localShortPricing.ts`...).
- There is no way to enter sizes, and no per-length pricing.

## 3. How the layout is worked out (non-technical)

Think of placing tiles on a long table, trying to use as little table length as possible.

1. **Big designs first.** Small ones can fill leftover corners later; big ones can't.
2. **Keep a list of empty spaces.** At the start the whole roll is one empty space (23" wide).
   After each design is placed, the system notes the empty space **to its right** and **below it**.
3. **Fit check.** A design fits a space if
   `design width + 0.5 ≤ space width` and `design height + 0.5 ≤ space height`.
   If it doesn't fit, try it **rotated 90°**.
4. **First line or next line?** Among all spaces where it fits, pick the **highest one** (closest
   to the top of the roll). Only if nothing fits up top does it go further down (next line).
5. **Length used** = bottom edge of the lowest design. **Price** = length in meters (rounded) × 1,500.

Technical name: 2D strip packing, **MaxRects** algorithm (best-short-side / bottom-left rule).
The gap is handled by adding 0.5" to every design and treating the roll as 23.5" wide,
so the last design in a line doesn't need a gap after it.

## 4. Worked example

Order: **A = 15×10** (1 pc), **C = 18×8** (1 pc), **B = 3×3** (6 pcs)

1. **A** placed top-left. Space to its right: 23 - 15 - 0.5 = **7.5"** wide, 10" tall.
2. **C (18")**: right space 7.5" → no fit (rotated 8" → still no fit). Goes below A, starting at 10.5".
3. **B (3×3) × 6**: fits in the 7.5" space next to A.
   - Across: 3 + 0.5 + 3 = 6.5 ≤ 7.5 → 2 per line
   - Down: 3 + 0.5 + 3 + 0.5 + 3 = 10 ≤ 10 → 3 lines
   - 6 logos next to A, no extra length. (A 7th would go next to C: 23 - 18 - 0.5 = 4.5" free.)

```
|<---------------- 23" ---------------->|
+---------------+ [B] [B]               |
|   A  15×10    | [B] [B]               |
|               | [B] [B]               |
+---------------+                       |
+--------------------+                  |
|    C  18×8         |                  |
+--------------------+                  |
```

4. Length = 10 + 0.5 + 8 = **18.5"** = 0.47 m → rounded to **0.5 m** → **Rs 750**

## 5. Proposed screen flow

When Category = **DTF**, the normal Quantity/Rate fields are replaced by:

```
Design name | Width (in) | Height (in) | Qty | [x]
Logo front  |    15      |    10       |  1  |
Small logo  |     3      |     3       |  6  |
[+ Add design]

┌──── Roll preview (23" wide) ────┐
│ █████████  ▪ ▪                  │
│ █████████  ▪ ▪                  │
│ ███████████████                 │
└─────────────────────────────────┘
Length used: 18.5" (0.47 m) → charged 0.5 m
Total: Rs 750
[+ Add to Quotation]
```

- Price and preview update **instantly** on every keystroke (calculated in the browser, no API call).
- Error if a design is wider than the roll even when rotated (e.g. 25×25).
- The whole DTF job is added to the cart as **one line**:
  - `category: 'DTF'`, `quantity: 1`, `unitPrice = total`
  - `category_fields: { Designs: "Logo front 15×10 ×1, Small logo 3×3 ×6", Length: "0.5 m" }`
- Because it uses the existing cart line shape, backend save, PDF and View Quotation need **no change**.

## 6. Implementation plan

| File | Change |
|---|---|
| `lib/localDtfPricing.ts` (new) | Config: roll width 23, meter 39, Rs 1,500/m, gap 0.5, rounding step, minimum. Same "local, testing only, move to DB later" pattern as `localTshirtPricing.ts`. |
| `lib/dtfPacking.ts` (new) | Pure function `packDtf(designs, config)` → `{ placements, usedLength, meters, price, errors }`. MaxRects, ~100 lines, no new npm package. |
| `app/(invoices)/quotation/page.tsx` | If category is DTF: design rows form, `useMemo(packDtf)`, SVG roll preview, add one cart line. |
| DTF category in DB / local override | Make "DTF" appear in the Category dropdown. |

Later: move DTF config to the DB (Ideal Pricing page); optionally re-check the price in the
backend (`backend/src/routers/quotation.py`) so it can't be changed from the browser.

## 7. Decisions

- [x] **Units:** inches.
- [x] **Rounding:** up to the next **half meter**, minimum 0.5 m.
- [x] **Rotation:** yes, auto 90°, with a per-design "Rotate" tick to turn it off.
- [x] **Sub-categories of DTF:** only "By Size (Gang Sheet)" for now.
- [ ] **Edge margin:** any blank margin needed at the roll edges (left/right/start)? (none for now)
- [ ] **Rush charge:** a DTF job is saved as qty 1, so a rush deadline adds 1 × rush rate. Is that right for DTF?
- [ ] Same DTF form in **Customer Invoice** too?
- [ ] "DTF" category: not in the DB yet, so the Quotation page adds it locally when missing.
