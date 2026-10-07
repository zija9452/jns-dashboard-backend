---
id: 11
title: Dynamic dye pricing settings
stage: general
date: 2026-10-07
surface: agent
model: claude-opus-5-5
feature: none
branch: none
user: zijayaseen15
command: none
labels: ["pricing", "dye", "customer-category", "ideal-pricing", "migration"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - backend/add_required_tables_in_database/add_dye_pricing.py
 - backend/src/models/customer_category.py
 - backend/src/routers/customer_category.py
 - backend/src/utils/mockup_charges.py
 - backend/src/routers/quotation.py
 - backend/src/routers/customer_invoice.py
 - frontend/dashboard/frontend/lib/quantityPricing.ts
 - frontend/dashboard/frontend/components/QuantityTierCards.tsx
 - frontend/dashboard/frontend/app/(invoices)/quotation/page.tsx
 - frontend/dashboard/frontend/app/(invoices)/customer-invoice/page.tsx
 - frontend/dashboard/frontend/app/(pages)/customer-category/page.tsx
 - frontend/dashboard/frontend/app/(pages)/ideal-pricing/page.tsx
 - DYE_PRICING.md
tests:
 - tsc --noEmit (exit 0)
 - 15 pricing logic cases (default + custom rates, unticked dye, mixed orders) - all PASS
 - parse_mockup_charges with dye map: mixed accepted, dye-only rejected
 - add_dye_pricing.py run on both branch DBs
---

## Prompt

ye code me change kia he ??dynamic nnhi he kia ??

hn , chackbox de do , or update kr do dynamic

## Response

- Dye is now set from a per-option "Dye" checkbox on the Customer Category page, stored in `sub_categories[].dye_options`.
- Each category's dye multipliers (1-4 / 5-15 pcs) are set on the Ideal Pricing page: `customer_categories.dye_rate_single` / `dye_rate_qty`, default 2 / 1.5.
- The migration added the columns in both branches and ticked the existing Dye options.
- The frontend and backend no longer detect dye by option name.
