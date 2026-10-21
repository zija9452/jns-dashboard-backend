---
id: 13
title: Warehouse prices set by invoice
stage: general
date: 2026-10-21
surface: agent
model: claude-opus-5-5
feature: none
branch: none
user: zijayaseen15@gmail.com
command: none
labels: ["warehouse", "multi-branch", "pricing"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - src/routers/products.py
 - src/routers/warehouse_invoice.py
 - src/services/branch_transfer.py
 - ../frontend/dashboard/frontend/app/(warehouse)/warehouse-products/page.tsx
 - ../frontend/dashboard/frontend/app/(warehouse)/warehouse-stock/page.tsx
 - ../frontend/dashboard/frontend/app/(warehouse)/warehouse-invoice/page.tsx
 - ../frontend/dashboard/frontend/app/api/warehouse-invoice/route.ts
tests:
 - python ast syntax check (no local venv, modules not imported)
 - npx tsc --noEmit (clean)
---

## Prompt

warehouse ki add product me prce and cost price ko optional kro ... select branch ka option bhi remove kro ... stock page se bhi warehouse k branch col remove kr do , or warehouse k hi add product me warehouse ka stock ka or vendor ka input bhi do , or inhen bhi optional rkho ...
(follow-ups) dono me hi alg alg prices rkhwani hen ... invoice bnaty wakt warehouse ki , hn den ge shop ki cost and selling price ...
jb invoice bne gi , to usi wakt cost an dprice dale ajyen ge na , to warehouse se ye cols remove kr den ge hm ... kia professional he ?
option 1 , ab pura short me btao kia kia hoga
yes

## Response snapshot

Option 1: warehouse product form has no price/cost/branch (backend sets branch; new products start at price 0); optional opening warehouse stock + vendor runs the existing stock-in. Warehouse invoice picks customer first, prefills Rate (shop cost) and Shop Selling Price from that customer's branch DB, requires both > 0, and on save sets cost_price/unit_price + stock in that branch only (LH row directly, KA via branch_transfer). Branch column removed from warehouse stock page.

## Outcome

- ✅ Impact: per-branch shop prices are set by the warehouse invoice
- 🧪 Tests: syntax + tsc only; not run end-to-end
- 📁 Files: see files list
- 🔁 Next prompts: test create product with stock+vendor, LH invoice, KA invoice
- 🧠 Reflection: product edit no longer sends price/cost, so it can't overwrite shop prices

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
