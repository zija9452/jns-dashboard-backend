---
id: 15
title: Warehouse product optional shop prices
stage: general
date: 2026-10-24
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
 - src/services/product_mirror.py
 - ../frontend/dashboard/frontend/app/(warehouse)/warehouse-products/page.tsx
tests:
 - backend import inside backend-api-1 container
 - tsc --noEmit (clean)
---

## Prompt

ok , ab warehouse add product me cost and sell price ka input bhi do , lekin optional dena , agr user ne de dia sui wakt cost and sell price to wraehouse ki invoice bne gi , otherwise invoice bnaty wakt lazmi deni he ye already he ,  btao kia kro ge ?? or cost and sell dono branches me yhi rhe gi , jese complete data or barcode same rehte ehn
(follow-up) 1. sirf input de do na customer jo bhi amout dale , bs ye he k k agr invoice k wakt amount change kre to change wali jaye invoice me , ye already hota he ye confirm kr do bs , or short me btao ek baat rule :ok , mene hi set kia he , 1, alg input rkho, 2 dono ki kr do change

## Response snapshot

Confirmed invoice-time Rate/Shop Price changes go into the invoice and that branch's product. Added optional "Shop Cost" and "Shop Selling Price" inputs (no validation) to warehouse Add/Edit Product. Create sends them (product mirror copies to Karimabad). Edit sends them only when changed; backend `mirror_prices` sets the same cost/price on the other branch's product by barcode.

## Outcome

- ✅ Impact: warehouse invoices prefill Rate / Shop Price from these values in both branches
- 🧪 Tests: import + tsc only; not run end-to-end
- 📁 Files: see files list
- 🔁 Next prompts: test add with prices, edit price, invoice prefill LH + KA; deploy
- 🧠 Reflection: edit sends prices only when changed so other edits keep invoice-set branch prices

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
