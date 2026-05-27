---
description: Ensure a price line is present before clicking Buy Now to avoid empty
  answers.
name: verify_price_before_buy_now
provenance:
  action: ADD
  epoch: 2
  fixes: 7
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 4
  - 52
  - 8
  - 188
  - 96
  - 48
  - 144
  - 68
  - 148
  - 182
  update_cycle: 1
tags:
- price
- buy now
- price verification
version: 1
---

# Verify Price Display Before Purchasing

## Pattern Description
When the instruction includes a price ceiling (e.g., "price lower than $40"), the agent must confirm that the currently opened product page actually displays a line beginning with `Price:` before issuing a `click_action` with the value `Buy Now`.  Clicking `Buy Now` on a page that does not expose the price prevents the agent from emitting the required final answer (the price), leading to an empty answer string. This skill adds a lightweight verification step that protects the full‑reward path without adding extra search rounds.

## When to Use This Skill
- When the instruction contains a price constraint such as "price lower than $X" or "under $X".
- When the observation after a `click_action` to a product shows option selectors (color, size, etc.) but **no** line starting with `Price:`.
- When the list of available actions includes `Buy Now`.

## Failure Pattern
- Clicking `Buy Now` while the observation lacks a `Price:` line, causing the agent to emit an empty final answer.
- Clicking `Buy Now` before confirming that the displayed price satisfies the ceiling, leading to a partial reward or failure.
- Selecting required options and then immediately clicking `Buy Now` on a page where the price is hidden until after the purchase step.

## Action Rule
**Rule 1: primary behavior**
1. After a `click_action` that opens a product page, scan the observation for a line that begins with `Price:`.
2. If the line exists, verify that the numeric value is ≤ the ceiling from the instruction.
3. Only then issue `click_action(value="Buy Now")`.

**Rule 2: fallback**
- If no `Price:` line is present, do **not** click `Buy Now`. Instead:
  - If the observation lists a `Back to Search` or `< Prev` button, `click_action` that button to return to the results page and select a different candidate that shows a price.
  - If the page offers a secondary tab or detail view (e.g., "Details", "More info"), click that option to reveal the price before buying.
  - If neither is available, re‑`search_action` with the same keywords but include the word `price` to force results that surface the price directly.

## Verification Rule
- Confirm the presence of `Price:` in the observation **before** any `Buy Now` click.
- Ensure the numeric price extracted (strip any currency symbols) is ≤ the price ceiling parsed from the instruction.
- If the price is higher than the ceiling, treat the item as unsuitable and go back to search.

## Do Not
- Do not click `Buy Now` while any requested option (color, size, quantity, etc.) remains unselected.
- Do not click a value that is not listed in the current `clickables`.
- Do not assume the price is hidden; always look for an explicit `Price:` line.

## Example Trajectory
**WRONG trajectory:**
Instruction: "find me a black fast wireless universal charging stand, and price lower than $40"
```
Turn 1: Think → Need a product, search.
Turn 2: Act → search_action(keywords="black fast wireless universal charging stand under $40")
Turn 3: Obs → results list, clickables include product IDs.
Turn 4: Think → Open first candidate.
Turn 5: Act → click_action(value="b09qpqvwjs")
Turn 6: Obs → product page shows options but **no** line starting with "Price:".
Turn 7: Think → (mistakenly) assume price is okay.
Turn 8: Act → click_action(value="Buy Now")
Turn 9: Obs → purchase confirmation page, no price line.
Turn 10: Final answer → "" (empty) → FAIL
```
**CORRECT trajectory:**
Instruction: same as above
```
Turn 1: Think → Need a product, search.
Turn 2: Act → search_action(keywords="black fast wireless universal charging stand under $40")
Turn 3: Obs → results list.
Turn 4: Think → Open candidate.
Turn 5: Act → click_action(value="b09qpqvwjs")
Turn 6: Obs → product page shows options **and** a line "Price: $36.95".
Turn 7: Think → Verify price ≤ 40 → OK.
Turn 8: Act → click_action(value="Buy Now")
Turn 9: Obs → purchase confirmation, price already known.
Turn 10: Final answer → "Price: $36.95" → PASS (reward 1.0)
```

## Notes
- This skill is orthogonal to option‑selection skills; it only gates the final purchase step.
- It works for any product type as long as the instruction mentions a price limit.
- Adding this verification does not increase the round count for already correct samples because a price line is typically present on the product page.
