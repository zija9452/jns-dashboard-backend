---
id: 10
title: Dye pricing no flat charges
stage: general
date: 2026-10-07
surface: agent
model: claude-opus-5-5
feature: none
branch: none
user: zijayaseen15
command: none
labels: ["pricing", "dye", "flat-charges", "quotation", "customer-invoice"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - frontend/dashboard/frontend/lib/quantityPricing.ts
 - frontend/dashboard/frontend/components/QuantityTierCards.tsx
 - frontend/dashboard/frontend/app/(invoices)/quotation/page.tsx
 - frontend/dashboard/frontend/app/(invoices)/customer-invoice/page.tsx
 - backend/src/utils/mockup_charges.py
 - DYE_PRICING.md
tests:
 - tsc --noEmit (exit 0)
 - lookupIdealPrice / repriceCart / needsMockup cases (x2, x1.5, normal, Oversize+ 300, mixed orders)
 - parse_mockup_charges: mixed accepted, dye-only rejected, dye-only 0 accepted
---

## Prompt

customer category me dekho , dye ki category hen , in me flat charges nnhi jahyen ge , agbr dye ho to , bs ye hoga k price k doub le charfge kren ge quantity (1-4) tk , or 5-15 tk (1.5 charg kren ge , mjese 500 ki he jersey to 750 len ge , or 16 ki normal hogi , edge case discuss kr len , or discuss kr len ,  or code is ka explore kr lo

Follow-ups:
- lets suppose ek jersey 950 kki he sb modikefiers select krne k bd , to us k double price dikhane hen dye me
- meri samjh nhi a rha he short me b btao , or hn jb double or 1.5 lerhee he to dye me flat charges nhi jayen ge
- order me agr dye and non dye hon to agr total quantity zyda hon 5 or 5 seto flat nhi lge a , bs dye double hoga , qk dye to 1-4 hoga na , or oversize me 4x kese hoga? 100 ka he to 100 or oversize k or 100 dye k , to 300 bne ga na
- confirmation: hn lge ga flat
- ok , or jin ka bill bn gya he , wo to change nhi hoga na ?

## Response

- Dye = any selected option whose name contains "Dye".
- The dye multiplier comes from the category's dye pieces: 1-4 = x2, 5-15 = x1.5, 16+ = normal.
- The tier still comes from all pieces of the category.
- The dye extra = (base + flat modifiers) x (multiplier - 1), added after Oversize+.
- The flat charge is applied only if the category has 1-4 pcs and at least one non-dye piece. The backend rejects a flat charge on a dye-only category.
- Saved bills are unchanged.
- Documented in DYE_PRICING.md.
