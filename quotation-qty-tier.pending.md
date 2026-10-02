# Pending: Quantity tier for mixed items in one Quotation

Status: **To discuss with manager** - no code changed yet.

## 1. The problem

The customer orders one team kit with 2 variations:
- 10 × T-shirt, Round Neck, **Half** sleeve, Polyzone 130gsm, Adult
- 10 × T-shirt, Round Neck, **Full** sleeve, Polyzone 130gsm, Adult

That makes **20 jerseys** in one quotation. Our rates are:

| | Single piece rate | Qty rate |
|---|---|---|
| Half sleeve | 950 | 900 |
| Full sleeve | 1000 | 950 |

Question: should these 20 jerseys get the single rate or the qty rate?

## 2. What the page does now

File: `frontend/dashboard/frontend/app/(invoices)/quotation/page.tsx`

- The tier is picked from **each cart line's own qty**, never from the cart total (`tierForQuantity` / `pickTierPrice`, `lookupIdealPrice`).
- Tiers in code: 1-4 (single), 5-15, 16-99, 100+.
- Once a line is added, its rate is fixed. Adding or removing other lines does not recalculate it.
- The backend (`backend/src/routers/quotation.py`, `_parse_items`) saves whatever rate the page sends.
- `lib/localTshirtPricing.ts` only has single-piece (`'1'`) prices. For 5+ pcs the Rate box stays empty and staff must type it.
- Customer Invoice (`customer-invoice/page.tsx`) has the same per-line rule.

What goes wrong today:
- 10 half + 10 full: counted as 10 and 10, not 20.
- 3 half + 3 full: 6 jerseys, but each line has 3 pcs, so the customer pays the single rate: 3×950 + 3×1000 = **5,850** instead of 3×900 + 3×950 = **5,550**.

## 3. How the real world handles it

| Approach | Who uses it |
|---|---|
| Each line separate (current behaviour) | Shopify built-in B2B price breaks, Odoo default pricelists |
| Qty of the same article counted together (sizes/colours/sleeves mixed) | Custom Ink (mixed sizes in one style keep the discount), Shopify volume apps "product-level", Odoo third-party module |
| Whole quote / group counted together | Salesforce CPQ ("Cross Products" + "Aggregation Scope = Quote/Group"), screen printers when the design is the same |

Custom apparel rule (Kustom Imprints): *"Our price breaks are based on the number of same design items, not similar garments."*

"Volume" pricing (the tier rate applies to all units, which fits our case) differs from "slab" pricing (different rates for different portions of the qty).

## 4. Recommendation

- **Count the pieces of the same main category (e.g. all T-shirts) across the whole quotation.** That total picks the tier.
- Each line keeps its own options/modifiers (Full sleeve = +50).
- Different categories (T-shirt vs Short) are counted separately.
- Use only **2 tiers**: 1-4 = single, 5+ = qty, to match our real price list.

Result for the example: 20 T-shirts get the qty rate.
- Half: 10 × 900 = 9,000
- Full: 10 × 950 = 9,500
- **Total = 18,500**

## 5. Proposed screen flow

1. **Item form:** the tier hint counts the cart too, e.g. "Qty rate: 20 T-shirts in quotation (10 already added + 10)".
2. **Add item:** all auto-priced lines of that category are recalculated. The old rate is shown struck out, and a toast says "T-shirt lines updated to Qty rate (20 pcs)".
3. **Cart header:** a label per category, e.g. `T-shirt: 20 pcs → Qty rate`, or `Short: 3 pcs → Single rate · 2 more pcs for Qty rate`.
4. **Remove item:** if the total drops below 5, the lines go back to the single rate and a toast explains it.
5. **Manual rate:** a rate typed by staff is tagged `manual` and never recalculated.
6. **Missing price:** if the new tier has no price, the row shows a warning "no qty price - check rate".
7. **PDF:** shows the final rates only (optionally a note "Qty rate applied - 20 pcs").

Later option: an "article card" layout (pick T-shirt + Neck + Fabric once, then add rows for sleeve/size with qty each), like Custom Ink. This is a bigger UI change.

## 6. Decisions needed from manager

- [ ] Count per **main category** (recommended), per exact article, or across the whole quotation?
- [ ] 2 tiers (1-4 / 5+) or keep 4 tiers (1-4 / 5-15 / 16-99 / 100+)?
- [ ] Qty (5+) prices for every Neck style: T-shirt only has single-piece prices now. The same is needed for Short, Trouser, Jacket, Hoodie Jacket and Sando.
- [ ] Apply the same rule to Customer Invoice too?
- [ ] Show the "Qty rate applied" note on the PDF?

## Sources

- https://kustomimprints.com/custom-services/screen-printing/price-breaks/
- https://www.customink.com/tools/wholesale-t-shirts-sweatshirts
- https://community.shopify.com/t/tiered-discounts-based-on-variant-quantity/569396
- https://www.odoo.com/forum/help-1/how-to-set-pricelist-rule-discount-for-a-multiple-product-variants-in-the-same-so-odoo-10-114989
- https://trailhead.salesforce.com/content/learn/modules/discounting-tools-in-salesforce-cpq/configure-quantities-for-discount-schedules
- https://help.salesforce.com/s/articleView?id=sales.cpq_discount_schedules.htm&language=en_US&type=5
