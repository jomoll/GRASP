---
description: "Block Buy\u202FNow clicks unless a visible Price line satisfies the\
  \ instruction\u2019s ceiling."
name: require_price_before_buy_now
provenance:
  action: MODIFY
  epoch: 9
  fixes: 3
  parent_version: 1
  probe_score: 5
  regressions: 3
  triggering_sample_ids:
  - 152
  - 44
  - 22
  - 144
  - 120
  - 46
  - 16
  - 42
  - 156
  - 56
  update_cycle: 1
tags: []
version: 2
---

# Block Buy Now Without Visible Price

## Pattern Description
When an instruction includes a price ceiling (e.g., “under $50”, “price lower than 30 dollars”), the agent must only purchase an item after confirming that the product detail page shows a `Price:` line and that the numeric value is **≤** the ceiling. This prevents buying when the price is hidden, ambiguous, or exceeds the budget, which otherwise leads to wasted turns and empty final answers.

## When to Use This Skill
- The instruction contains a price‑related phrase such as **under $X**, **price lower than X dollars**, or **cost less than $X**.
- The current observation is a product detail page (i.e., `Buy Now` appears in the clickables list).
- No `Price:` line has been seen on this page yet.

## Failure Pattern
- `click_action(value="Buy Now")` executed while the observation lacks a line that starts with `Price:`.
- The agent proceeds to buy an item whose price is unknown, causing a task‑limit hit and an empty final answer.
- Example action values to avoid: `click[Buy Now]` when `Price:` is absent.

## Action Rule
**Rule 1: Primary behavior**
1. After opening a candidate item (via `click_action` on an item ID), scan the observation for a line matching `Price:`.
2. If a price line is present, parse the numeric amount.
3. Compare the amount to the ceiling extracted from the instruction.
4. Only then issue `click_action(value="Buy Now")`.

**Rule 2: Fallback**
- If no price line is present, or the price exceeds the ceiling, execute a safe navigation action such as `click_action(value="Back to Search")` or `click_action(value="< Prev")` and optionally re‑search with a tighter keyword set.

## Verification Rule
- Confirm that the observation contains `Price: $<amount>`.
- Ensure `<amount>` ≤ the ceiling extracted from the instruction.
- Verify that all required option buttons (size, color, count, etc.) have been selected before buying.

## Do Not
- Do not click `Buy Now` while any price line is missing.
- Do not click `Buy Now` if the parsed price is greater than the instruction’s ceiling.
- Do not assume a price exists just because the item appears in the search results.
- Do not click a value not listed in the available‑actions list.

## Example Trajectory
**WRONG trajectory:**
Instruction: "find cookies made with high fructose, and price lower than 50 dollars"
Turn 1: `search_action(keywords="high fructose cookies")` → results listed
Turn 2: `click_action(value="b00myrxwos")` → item page **without** a `Price:` line
Turn 3: `click_action(value="Buy Now")` → purchase attempted → task limit reached, no final answer
→ **FAIL** (price never verified)

**CORRECT trajectory:**
Instruction: "find cookies made with high fructose, and price lower than 50 dollars"
Turn 1: `search_action(keywords="high fructose cookies")` → results listed
Turn 2: `click_action(value="b00myrxwos")` → item page shows `Price: $9.16`
Turn 3: Verify $9.16 ≤ $50 → condition satisfied
Turn 4: `click_action(value="Buy Now")` → purchase succeeds
Turn 5: Emit final answer with price
→ **PASS** (price validated before buying)

## Notes
- This skill supersedes the older `require_price_before_buy_now` version whose checks were too permissive.
- It works for any product type as long as the instruction mentions a price ceiling.
