---
description: "Automatically click\u202FBuy\u202FNow once a displayed price satisfies\
  \ the instruction\u2019s ceiling and all required options have been chosen."
name: auto_buy_when_price_within_budget_and_options_selected
provenance:
  action: ADD
  epoch: 7
  fixes: 3
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - 84
  - 92
  - 184
  - 146
  - 60
  - 66
  - 68
  - 108
  - 2
  - 126
  update_cycle: 0
tags: []
version: 1
---

# Auto‑Buy When Price Meets Budget After All Required Options Selected

## Pattern Description
When the instruction explicitly mentions a price ceiling (e.g., “price lower than $40”) you must purchase the item **only after** every required option (size, color, quantity, pack, etc.) has been selected **and** the displayed price is at or below that ceiling.  Instead of waiting for a separate decision step, the agent should automatically issue a `click_action` for `Buy Now` as soon as those conditions are observed.  This prevents two common failures: (1) buying too early before options are set, and (2) ending the episode with an empty answer because the agent never clicks `Buy Now` even though a valid product is on the page.

## When to Use This Skill
- The instruction contains a phrase like “price lower than $X”, “under $X”, or “cost not more than $X”.
- After a `click_action` you observe a line `Price: $Y` in the observation.
- The observation **does not** list any of the option categories that were present before (e.g., `size`, `color`, `quantity`, `pack`, `material`, `flavor`).  This indicates that all required options have already been chosen.
- The numeric price `$Y` is **≤** the ceiling `$X`.
- The available actions include `Buy Now`.

## Failure Pattern
- **Premature purchase:** Clicking `Buy Now` before all required options are selected, resulting in a partially‑matching purchase and a reduced reward.
- **Empty answer:** Never clicking `Buy Now` after a suitable product is displayed, causing the episode to hit the turn limit and return an empty answer string.
- **Over‑budget purchase:** Clicking `Buy Now` when the displayed price exceeds the ceiling (the existing `verify_price_before_buy_now` skill should block this, but it is not triggered if the agent never attempts a purchase).

## Action Rule
**Rule 1: primary behavior**
After any `click_action`, if **all** of the following hold, immediately issue:
```json
click_action({"value": "buy now"})
```
- The instruction contains a price ceiling.
- The latest observation includes a line matching `Price: $<num>`.
- `<num>` ≤ the ceiling extracted from the instruction.
- No option categories (e.g., `size`, `color`, `quantity`, `pack`, `material`, `flavor`) appear among the current clickables.
- `Buy Now` is present in the clickables list.

**Rule 2: fallback**
If the price line is missing or exceeds the ceiling, do **not** auto‑buy; let the existing `verify_price_before_buy_now` skill handle blocking, and continue normal navigation (search for another item, change options, etc.).

## Verification Rule
Before emitting the automatic `Buy Now` click, double‑check that:
- The observation contains a `Price:` line and the numeric value is parsed correctly.
- The parsed price is ≤ the instruction’s ceiling.
- All required option categories that were listed earlier are no longer present in the clickables (meaning they have been selected).
- The `Buy Now` button is actually clickable.
If any check fails, abort the auto‑buy and continue the normal flow.

## Do Not
- Do not click `Buy Now` while any required option category is still visible (e.g., `size`, `color`, `quantity`).
- Do not click `Buy Now` when the observed price exceeds the stated ceiling.
- Do not click a value that is not listed in the current `clickables` set.
- Do not issue a second `Buy Now` click after one has already been sent.

## Example Trajectory
**WRONG trajectory (fails to auto‑buy):**
Instruction: “I want a blue 32 GB USB flash drive, quantity 3, under $40.”
```
Turn 1: think → search_action(keywords="blue 32GB USB flash drive under $40")
Turn 2: act  → click_action(value="b08k4fn9l6")               # open product page (shows size options)
Turn 3: think → click_action(value="32gb-3pack")            # select quantity pack
Turn 4: act  → click_action(value="blue")                  # select color
Turn 5: think → (no further action)                         # agent stops, never clicks Buy Now → FAIL (empty answer)
```
**CORRECT trajectory (auto‑buy triggers):**
```
Turn 1: think → search_action(keywords="blue 32GB USB flash drive under $40")
Turn 2: act  → click_action(value="b08k4fn9l6")               # open product page (size/quantity/color listed)
Turn 3: think → click_action(value="32gb-3pack")            # select quantity pack
Turn 4: act  → click_action(value="blue")                  # select color (observation now shows Price: $38.99 and no size/color options remain)
Turn 5: think → auto‑buy rule fires → click_action(value="buy now")   # purchased item within budget and all options set → PASS (reward 1.0)
```

## Notes
- The skill is safe because it only fires when the price line is present and all option categories have disappeared, a state that never occurs on a correct solution that already clicked `Buy Now` manually.
- It complements `verify_price_before_buy_now`; the latter still blocks over‑budget purchases, while this skill ensures the agent actually completes the purchase when the budget condition is satisfied.

---

**Tags:** ["price", "budget", "buy now", "auto purchase", "option selection"]
