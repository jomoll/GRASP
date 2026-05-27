---
description: Block Buy Now when the product page lacks a visible Price line and fallback
  to search again.
name: verify_price_before_buy_now
provenance:
  action: MODIFY
  epoch: 3
  fixes: 2
  parent_version: 1
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - 114
  - 126
  - 32
  - 28
  - 172
  - 22
  - 42
  - 2
  - 128
  - 4
  update_cycle: 1
tags:
- price
- buy now
- price verification
version: 2
---

# Verify Price Before Buy Now

## Pattern Description
When the instruction requires buying an item under a price ceiling, the agent must ensure that the product detail view actually displays a `Price:` line before issuing a `click_action` with `value="buy now"`. Clicking *Buy Now* on a page that does not expose a price leads to an empty answer string and a failed reward because the final answer cannot be generated.

## When to Use This Skill
- The instruction contains a price constraint (e.g., "price lower than $80", "under $40").
- The current observation lists `clickables` that include `"buy now"` **and** the observation text does **not** contain a line starting with `"Price:"`.
- The page still shows option selectors (size, color, quantity, etc.) but no price.

## Failure Pattern
- Clicking `Buy Now` while the observation lacks a `Price:` line, causing the system to return an empty answer string.
- Performing `click_action` with a value that is not present in the `clickables` list (e.g., clicking `Buy Now` after a failed price check).

## Action Rule
**Rule 1: primary behavior**
1. After opening a candidate item, scan the observation for a line that begins with `"Price:"`.
2. If a `Price:` line is present, proceed with the normal workflow (select any required options, then `click_action(value="buy now")`).

**Rule 2: fallback**
- If no `Price:` line is found:
  - If `click_action` offers a `"back to search"` or `"< Prev"` button, click that to return to the results list.
  - Otherwise, issue a new `search_action` with the original keywords plus the word `"price"` to surface items that display pricing.

## Verification Rule
- Before issuing `click_action(value="buy now")`, confirm:
  - The observation includes `"Price:"` followed by a numeric value.
  - The numeric value satisfies the instruction’s price ceiling.
  - All requested options (size, color, count, etc.) have been selected.

## Do Not
- Do not click `Buy Now` when the price line is missing.
- Do not assume the price is present just because the item appears in the search results.
- Do not click a value that is not listed in the `clickables` array.
- Do not skip option selection to reach `Buy Now` faster.

## Example Trajectory
**WRONG trajectory:**
Instruction: "i want a easy install roller shades window treatment size w45*h56 in color pastel blue, and price lower than 80 dollars"
Turn 1: `search_action(keywords="roller shade pastel blue 45x56 easy install")` → results listed
Turn 2: `click_action(value="b08bftq44z")` → item page shows color options but **no** `Price:` line
Turn 3: `click_action(value="buy now")` → agent proceeds, system returns empty answer → **FAIL**

**CORRECT trajectory:**
Instruction: same as above
Turn 1: `search_action(keywords="roller shade pastel blue 45x56 easy install")` → results listed
Turn 2: `click_action(value="b08bftq44z")` → item page shows color options, **no** `Price:` line
Turn 3: `click_action(value="back to search")` (fallback because price missing) → returns to results list
Turn 4: `search_action(keywords="roller shade pastel blue 45x56 easy install price")` → new results that include price information
Turn 5: `click_action(value="b08bftq44z")` → item page now contains `Price: $75.99`
Turn 6: `click_action(value="pastel blue")` → selects required color
Turn 7: `click_action(value="buy now")` → purchase succeeds, price verified ≤ $80 → **PASS**

## Notes
- This skill is a *constraint* that prevents an illegal `Buy Now` click; it does not add extra search rounds unless the price is missing.
- It works for any product type where the price may be hidden behind lazy‑loading or collapsed sections.
