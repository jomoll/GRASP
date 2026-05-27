---
description: "Block Buy\u202FNow clicks unless a visible Price line is present and\
  \ satisfies the instruction\u2019s price ceiling."
name: require_price_before_buy_now
provenance:
  action: ADD
  epoch: 9
  fixes: 4
  probe_score: 1
  regressions: 3
  triggering_sample_ids:
  - 4
  - 50
  - 126
  - 188
  - 68
  - 160
  - 28
  - 154
  - 96
  - 142
  update_cycle: 0
tags:
- price
- budget
- under
- lower than
- cost
version: 1
---

# Require Visible Price Before Buying

## Pattern Description
When the instruction specifies a price ceiling (e.g. "price lower than $50" or "under $30"), the agent must **never** click `Buy Now` unless the current observation shows a line that begins with `Price:` and the numeric value on that line is **≤** the stated ceiling. This prevents purchases that never actually occur (the platform shows no price), which in turn avoids empty final answers.

## When to Use This Skill
- When the instruction contains a price ceiling phrase such as "price lower than $X", "under $X", "cost less than $X", etc.
- After any click that opens a product detail page or changes a selectable option (size, color, pack, etc.).
- If you see a `Buy Now` button but **no** `Price:` line in the observation.

## Failure Pattern
- Clicking `Buy Now` while the observation lacks a `Price:` line, causing the purchase to fail and the agent to return an empty answer.
- Clicking `Buy Now` when the displayed price exceeds the ceiling, or when the price line disappears after an option selection.
- Selecting required options, then clicking `Buy Now` without re‑checking that a price is still visible.

## Action Rule
**Rule 1: primary behavior**
1. Scan the observation for a line that starts with `Price:`.
2. If found, extract the numeric value (ignore currency symbols, commas, and trailing text).
3. Compare the extracted price to the ceiling from the instruction.
   - If `price ≤ ceiling`, issue `click_action({"value": "Buy Now"})`.
   - If `price > ceiling`, treat the item as unsuitable: `click_action({"value": "back to search"})` (or `click_action({"value": "< Prev"})` if available) and optionally re‑search with refined keywords.
**Rule 2: fallback when price line missing**
- If no `Price:` line is present, **do not** click `Buy Now`.
- Immediately click a navigation action that returns to the search list (`back to search`, `< Prev`, or `Back to Search`).
- Optionally issue a new `search_action` with the same keywords or a narrower set (e.g., include the price ceiling term) to find a product that displays a price.

## Verification Rule
Before emitting `Buy Now`:
- Confirm the observation contains `Price:`.
- Verify the numeric price is ≤ the ceiling extracted from the instruction.
- Ensure all required options have been selected (they appear as selected/echoed in the observation).

## Do Not
- Do not click `Buy Now` when any requested option is still unselected.
- Do not click `Buy Now` if the observation does **not** contain a visible `Price:` line.
- Do not assume a price is present simply because the product title mentions a price.
- Do not ignore the price ceiling; always enforce the numeric comparison.

## Example Trajectory
**WRONG trajectory:**
Instruction: "find a wireless charger under $40."
Turn 1: `search_action({"keywords": "wireless charger under $40"})` → results listed.
Turn 2: `click_action({"value": "b09qpqvwjs"})` → product page shows **no** `Price:` line, but options are selectable.
Turn 3: `click_action({"value": "Buy Now"})` → purchase fails, later the agent outputs an empty answer.
→ **FAIL** (price missing → empty answer)

**CORRECT trajectory:**
Instruction: "find a wireless charger under $40."
Turn 1: `search_action({"keywords": "wireless charger under $40"})` → results listed.
Turn 2: `click_action({"value": "b09qpqvwjs"})` → product page shows **no** `Price:` line.
Turn 3: `click_action({"value": "back to search"})` → returns to results list.
Turn 4: `search_action({"keywords": "wireless charger $30 $40"})` → new results where a product displays `Price: $35.00`.
Turn 5: `click_action({"value": "b09newproduct"})` → observation shows `Price: $35.00`.
Turn 6: `click_action({"value": "Buy Now"})` → purchase succeeds, final answer can be emitted.
→ **PASS** (price verified before buying)

## Notes
- This skill is a strict constraint; it never adds extra rounds beyond the necessary navigation back‑search loop.
- It works for any product type because the check is based solely on the presence of a `Price:` line and the numeric comparison.
- The skill relies only on the instruction’s price phrase, which is always observable before the first tool call.
