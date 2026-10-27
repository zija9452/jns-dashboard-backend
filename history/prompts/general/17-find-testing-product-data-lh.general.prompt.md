---
id: 17
title: Find testing product data in LH
stage: general
date: 2026-10-27
surface: agent
model: claude-opus-5-5
feature: none
branch: none
user: zijayaseen15
command: none
labels: ["data-cleanup", "testing-data", "light-house"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - none (read-only DB queries)
tests:
 - none
---

## Prompt

k testing nam ka product , stock entry , vendor payment is ki , or bill is k , ye btao kiakia he , delete krna he , abhi testing k ;liye use kiye he

(follow-up: light house me)

## Response snapshot

Read-only queries on the Light House DB found: product "testing" (barcode 690007129, stock 2); 4 stock entries (IN 5 from J&S Sports STOCK_IN_20261027_091052, SALE SIN-1303/1304/1305); 3 walk-in bills SIN-1303 (26-10), SIN-1304 (24-10), SIN-1305 (25-10), Rs 1000 cash each, with no proofs or refunds; daily_cash +1000 on 24, 25 and 26-10 (the 25-10 row was created only by the test); J&S Sports balance +4750 from the stock-in, with no vendor payment record. There is also an unused customer "testing" (2026-09-25). Nothing was deleted.

## Outcome

- ✅ Impact: list of test data for the user to approve before deletion
- 🧪 Tests: none
- 📁 Files: none
- 🔁 Next prompts: user approval → cleanup script (Docker backend-api-1)
- 🧠 Reflection: deleting the test data must also reverse daily_cash and the vendor balance, not only delete rows

## Evaluation notes (flywheel)

- Failure modes observed: Git Bash path conversion broke docker exec paths (fixed with MSYS_NO_PATHCONV=1)
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
