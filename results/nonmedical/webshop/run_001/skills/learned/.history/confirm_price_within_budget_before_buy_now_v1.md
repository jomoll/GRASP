---
description: Block Buy Now when no price line is visible or price exceeds the instruction's
  ceiling
name: confirm_price_within_budget_before_buy_now
provenance:
  action: ADD
  epoch: 5
  fixes: 2
  probe_score: 1
  regressions: 6
  triggering_sample_ids:
  - 58
  - 126
  - 18
  - 48
  - 92
  - 120
  - 54
  - 146
  - 184
  - 128
  update_cycle: 1
tags:
- price
- budget
- price ceiling
- under
- lower than
version: 1
---

# Confirm Price Within Budget Before Buying

## Pattern Description
When the instruction specifies a price ceiling (e.g., "price lower than $X" or "under $X"), the agent must verify that the product page actually displays a price and that the displayed price is **≤** the ceiling **before** issuing a `click_action(value="Buy Now")`. This prevents buying items that either lack a visible price or exceed the budget, which is a common source of empty‑answer failures.

## When to Use This Skill
- When the instruction contains a monetary constraint such as "price lower than", "under $", "budget", or "cost <".
- The current observation shows the list of **clickables** and includes `"Buy Now"` as an available action.
- The observation **does not** contain a line that starts with `"Price:"` followed by a dollar amount, **or** the extracted amount is greater than the ceiling.

## Failure Pattern
- Clicking `Buy Now` on a product page that shows no `Price:` line, resulting in an empty final answer.
- Clicking `Buy Now` on a product whose displayed price exceeds the budget, causing the agent to violate the instruction.
- The `verify_price_before_buy_now` skill fails to intervene because it only checks the *first* price line it sees and can miss cases where the price line appears after an option selection or is formatted differently.

## Action Rule
**Rule 1: Primary behavior**
1. Parse the instruction for a numeric price ceiling `C`.
2. If `"Buy Now"` is present in the `clickables` list, examine the latest observation text.
3. Search the observation for a line matching the regex `Price:\s*\$?([0-9]+(?:\.[0-9]+)?)`.
4. If a match is found, convert the captured value to a float `P`.
   - If `P ≤ C`, proceed to the next turn with `click_action(value="Buy Now")`.
   - If `P > C`, **do not** click `Buy Now`; instead, issue `click_action(value="Back to Search")` (or `< Prev` if available) to abort this candidate.
5. If **no** price line is found, also abort with `click_action(value="Back to Search")`.

**Rule 2: Fallback**
- If the observation contains option selectors (e.g., size, color) that have not yet been clicked, first complete those selections before re‑checking the price.
- After returning to search, refine the search keywords to include the price constraint explicitly (e.g., add "under $X" to the query) to increase the chance of landing on a priced item.

## Verification Rule
- Confirm the presence of a `Price:` line **and** that the numeric value satisfies `price ≤ ceiling`.
- Ensure that all requested options have been selected (they appear in the observation as highlighted or listed under the selected attribute).
- Only click `Buy Now` when both the price check and option‑selection checks pass.

## Do Not
- Do not click `Buy Now` when any required option button remains unselected.
- Do not click `Buy Now` if the price line is missing or the price exceeds the ceiling.
- Do not issue a `search_action` with the same keywords after a successful price verification; the purchase should complete.

## Example Trajectory
**WRONG trajectory:** (price line missing → agent buys anyway)
```
Instruction: "i would like a 2‑light bath vanity lighting set with nickel finish, and price lower than 160 dollars"
Turn 1: Think → search_action(keywords="2 light bath vanity lighting set nickel")
Obs: results listed, clickables=['search']
Turn 2: Think → click_action(value="b07szglt1b")   # opens item page, shows options but **no** "Price:" line
Obs: options for size & color, still no price line, clickables include ['Buy Now']
Turn 3: Think → click_action(value="Buy Now")   # violates skill, no price to verify
→ FAIL (empty answer)
```

**CORRECT trajectory:** (price present and within budget → purchase allowed)
```
Instruction: "i would like a 2‑light bath vanity lighting set with nickel finish, and price lower than 160 dollars"
Turn 1: Think → search_action(keywords="2 light bath vanity lighting set nickel")
Obs: results listed, clickables=['search']
Turn 2: Think → click_action(value="b07szglt1b")   # opens item page, shows size/color options and "Price: $108.20"
Obs: options listed, price line present, clickables include ['Buy Now']
Turn 3: Think → parse price $108.20 ≤ 160 → click_action(value="nickel")   # select required color
Obs: color selected, price still shown
Turn 4: Think → price still $108.20 ≤ 160 → click_action(value="Buy Now")
Obs: purchase confirmed, final answer includes "Price: $108.20"
→ PASS (reward 1.0)
```

## Notes
- The regex is tolerant to a missing dollar sign and to extra whitespace.
- If the price appears as `"$108.20"` without the "Price:" prefix, the skill still matches because the regex looks for the word "Price"; in that rare case, the fallback is to treat the line as missing and abort.
- This skill is orthogonal to option‑selection skills; it only gates the final `Buy Now` click based on price visibility and budget compliance.
