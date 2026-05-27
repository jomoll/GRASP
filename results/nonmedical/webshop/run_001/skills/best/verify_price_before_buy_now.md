---
description: "Block Buy\u202FNow only when the instruction explicitly contains a price\
  \ ceiling and the current observation (or a previously observed price) does not\
  \ satisfy that ceiling. The check is performed after clicks that open a product\
  \ detail page or change product options, but not after generic navigation actions\
  \ (e.g., next\u202F>, back\u202Fto\u202Fsearch, search). If a price line disappears\
  \ after an option click, the last seen price is reused."
name: verify_price_before_buy_now
provenance:
  action: MODIFY
  epoch: 6
  fixes: 6
  parent_version: 2
  probe_score: 2
  regressions: 6
  triggering_sample_ids:
  - 192
  - 48
  - 114
  - 188
  - 140
  - 126
  - 8
  - 80
  - 146
  - 162
  update_cycle: 0
tags: []
version: 3
---

# Verify Price Before Buying (Narrowed Trigger & Stateful Fallback)

## When to Activate
- **Price‑ceiling detection**: Activate this skill *only* if the instruction contains a price limit phrase.  The phrase is detected by the regex:
  ```regex
  (?i)(price\s+(lower|under|below|no\s+more\s+than|max|budget|cost).*?\$?\s*\d+|\$\s*\d+.*?(or\s+less|or\s+below|or\s+under))
  ```
- If the instruction does **not** match the above, the skill does nothing and the agent proceeds as usual.

## What Clicks Trigger a Price Check?
- Clicks whose `value` looks like a product identifier (Amazon ASIN) – e.g., matches `^b[0-9A-Z]{9,}$`.
- Clicks that select a product option (the value appears in the current observation under an *option* section).
- **Do NOT** run the price verification after generic navigation clicks such as `next >`, `prev`, `back to search`, or after a `search_action`.

## State Variable
- `last_price` – stores the most recent numeric price extracted from a `Price:` line (if any).  It is cleared when a new product page is opened.

## Rule 1: Primary Verification
1. After each qualifying `click_action` (product page open or option selection), scan the **latest observation** for a line matching `(?i)^Price:\s*\$?([0-9,.]+)`.
2. If the line is present, extract the numeric value, store it in `last_price`, and compare it to the ceiling extracted from the instruction.
3. If the extracted price exists **and** is ≤ the ceiling, allow the agent to continue (including a possible subsequent `Buy Now`).

## Rule 2: Fallback When Price Line Disappears
- If the price line is **missing** after an option‑selection click but `last_price` is set, reuse `last_price` for the comparison.
- If `last_price` is absent (i.e., no price has ever been seen on this product), treat the situation as **price unknown**.

## Rule 3: Abort / Backtrack
- **When price is unknown** *or* the price (whether newly seen or from `last_price`) exceeds the ceiling, **do not** click `Buy Now`.
- Instead, click the navigation action that returns to the results list (typically `back to search` or `Back to Search`).
- If no other candidates remain, the agent may re‑search with a more specific query that includes the price constraint.

## Verification Steps (Executed before any `Buy Now` click)
1. Confirm the instruction matched the price‑ceiling regex (otherwise skip the whole skill).
2. Ensure the current observation (or `last_price`) provides a numeric price.
3. Verify that the price ≤ the ceiling.
4. If any check fails, abort the purchase step as described in Rule 3.

## Do Not
- Click `Buy Now` while required options are still unselected.
- Assume a price is present just because it appeared earlier; always re‑check after each qualifying click, but reuse `last_price` if the line disappears.
- Apply the rule after generic navigation clicks.

## Example Adjusted Trajectory (price constraint present)
```
Turn 1: search_action(keywords="... under $40") → results list
Turn 2: click_action(value="b0xxxxxxx") → product page shows "Price: $38.99" (store last_price=38.99)
Turn 3: click_action(value="size L") → observation still contains price → ok
Turn 4: click_action(value="Buy Now") → price ≤ 40, purchase succeeds
```

## Example Adjusted Trajectory (price constraint absent)
```
Instruction has no price limit → skill does not run.
Agent may click Buy Now even if Price line is missing, preserving original behaviour.
```
