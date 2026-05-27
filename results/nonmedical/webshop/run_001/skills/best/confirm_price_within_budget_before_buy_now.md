---
description: "Block Buy\u202FNow when no price line is visible or price exceeds the\
  \ instruction ceiling, after any option selection"
name: confirm_price_within_budget_before_buy_now
provenance:
  action: MODIFY
  epoch: 6
  fixes: 4
  parent_version: 1
  probe_score: 2
  regressions: 4
  triggering_sample_ids:
  - 168
  - 184
  - 32
  - 142
  - 144
  - 164
  - 44
  - 138
  - 88
  - 22
  update_cycle: 1
tags:
- price
- budget
- visibility
- price ceiling
version: 2
---

# Block Buy Now When Price Is Missing or Over Budget

## Pattern Description
When the instruction contains a price ceiling (e.g. "price lower than $60"), you must never click `Buy Now` until the product detail page shows a visible `Price:` line that satisfies the ceiling. Many items hide the price until required options (size, color, quantity, etc.) are chosen. The safe workflow is: search → open candidate → select *all* required options → **only then** verify a price line exists and is ≤ ceiling → finally click `Buy Now`.

## When to Use This Skill
- The instruction explicitly mentions a price limit ("under $X", "price lower than $X", "budget $X").
- The current observation lists option buttons (size, color, quantity, pack count, etc.) **and** the `Buy Now` action is available.
- The observation **does not** contain a line starting with `Price:` (or the price is hidden behind a tooltip/selection).

## Failure Pattern
- Clicking `Buy Now` while the observation lacks a `Price:` line, resulting in an empty answer string.
- Clicking `Buy Now` after selecting options but the price line disappears, so the guard never triggers.
- Selecting options and then immediately clicking `Buy Now` without re‑checking the observation for a price.

## Action Rule
**Rule 1: Primary behavior**
1. After any `click_action` that selects an option, *re‑examine* the latest observation.
2. If a `Price:` line is present, extract the numeric value.
3. If the price is ≤ the ceiling, allow the next `click_action` to be `Buy Now`.
4. If the price is missing **or** exceeds the ceiling, **block** the `Buy Now` click and instead:
   - If price is missing, try another product by `click_action` on a different item id or `click_action` on `Back to Search` / `< Prev`.
   - If price exceeds the ceiling, go back to search and issue a tighter `search_action` (add "under $X" or reduce keywords).

**Rule 2: Fallback**
- If after selecting *all* required options the price still does not appear, treat the current item as invalid and issue `click_action` on `Back to Search` (or `< Prev`) to return to the results list.
- If the price appears but is over the ceiling, repeat the search with a stricter price filter (e.g. add "under $X" to keywords) before clicking any other item.

## Verification Rule
Before issuing `click_action(value="Buy Now")` you must confirm:
- The observation contains a line `Price: $<amount>`.
- `<amount>` parsed as a number is ≤ the ceiling extracted from the instruction.
- All required options (size, color, quantity, pack count, etc.) are selected (they appear in the observation as highlighted/selected tokens).
If any of these checks fail, do **not** click `Buy Now`.

## Do Not
- Do not click `Buy Now` when the price line is absent.
- Do not click `Buy Now` when the parsed price exceeds the instruction ceiling.
- Do not ignore required option selections; always verify they are present before checking price.
- Do not click a value that is not listed in the current `clickables` set.

## Example Trajectory
**WRONG trajectory:**
Instruction: "i'm looking for a navy large winter jacket, price lower than $60"
```
Think: Need a navy large jacket.
Act: search_action(keywords="navy large winter jacket under $60") → results list.
Think: Open first result.
Act: click_action(value="b09l15vx5x") → item page shows size/color options, **no price line**.
Think: Choose size.
Act: click_action(value="large") → still no price line.
Think: All options selected, click buy.
Act: click_action(value="Buy Now") → fails (empty answer).
```
**Why it fails:** `Buy Now` was clicked without a visible price.

**CORRECT trajectory:**
Instruction: "i'm looking for a navy large winter jacket, price lower than $60"
```
Think: Need a navy large jacket.
Act: search_action(keywords="navy large winter jacket under $60") → results list.
Think: Open first result.
Act: click_action(value="b09l15vx5x") → item page shows size/color options, **no price line**.
Think: Must select options then verify price.
Act: click_action(value="navy") → still no price.
Think: Select size.
Act: click_action(value="large") → price line now appears: "Price: $55.99".
Think: Price ≤ $60 and all options selected.
Act: click_action(value="Buy Now") → purchase succeeds.
```
The skill forces a re‑check after each option click and blocks the `Buy Now` click until a valid price is present and within budget.

## Notes
- This skill only intervenes on `Buy Now` clicks; it does not affect other navigation actions.
- It works for any product type as long as the instruction includes an explicit price ceiling.
