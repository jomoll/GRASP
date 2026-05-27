---
description: "Emit final answer immediately after a successful Buy\u202FNow click"
name: answer_after_purchase
provenance:
  action: MODIFY
  epoch: 1
  fixes: 2
  parent_version: 2
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - 52
  - 124
  - 46
  - 30
  - 102
  - 128
  - 16
  - 42
  - 78
  - 146
  update_cycle: 0
tags:
- buy now
- purchase
- final answer
version: 3
---

# Answer Immediately After Purchase

## Pattern Description
When the instruction requires buying a product, the agent must finish the episode right after the `click_action` that purchases the item. The episode should end with a concise JSON answer containing the `product_id`, any selected `options`, and the final `price`. No further tool calls are allowed after the purchase succeeds.

## When to Use This Skill
- **Good**: "When the instruction contains a purchase request and you have just executed `click_action` with a value that matches *buy now* (case‑insensitive)".
- **Good**: "When the observation after a click shows a `Buy Now` button was clicked and the page now displays product details (price, options)".
- **Bad**: "When the agent is still searching for items or selecting options".

## Failure Pattern
- Clicking `Buy Now` and then continuing to call `search_action` or `click_action` instead of answering, causing a task‑limit failure.
- Returning the internal product JSON (e.g., `{ "product_id": "B...", ... }`) without wrapping it in the final answer format.
- Omitting the final answer altogether after a successful purchase.

## Action Rule
**Rule 1: primary behavior**
1. Detect that the most recent tool call was `click_action` with `value` equal to **"buy now"** or **"Buy Now"** (case‑insensitive).
2. Verify that the current observation lists the purchased item (price, options) and that the available actions no longer contain a `search` bar.
3. Immediately output a JSON answer of the form:
   ```json
   {"product_id": "<id>", "options": {<selected_options>}, "price": "<price>"}
   ```
   where `<selected_options>` are the option values you clicked earlier.

**Rule 2: fallback**
- If the observation after the click does **not** contain a `Buy Now` confirmation (e.g., the click failed or the button was unavailable), do **not** emit the final answer; instead, continue the normal search/selection workflow.

## Verification Rule
- The last action must be a `click_action` on a value matching `buy now` (case‑insensitive).
- The observation should include a `price` line and the list of previously clicked option values.
- The set of available actions should *not* contain `search` (indicating we are on a product‑detail page after purchase).

## Do Not
- Do not issue any further `search_action` or `click_action` calls after the purchase.
- Do not wait for additional observations before answering.
- Do not output anything other than the concise JSON answer.
- Do not assume the product ID format; just copy the ID shown in the observation.

## Example Trajectory
**WRONG trajectory:**
Instruction: "... buy a body wash ... under $30"
- Turn 1: `search_action(keywords="dermatologist tested cucumber aloe body wash")` → results listed
- Turn 2: `click_action(value="b0049tuq48")` → product page with options
- Turn 3: `click_action(value="buy now")` → purchase succeeds **but** the agent calls `search_action` again instead of answering, eventually hitting the task limit.
→ **FAIL** (no final answer, task limit reached)

**CORRECT trajectory:**
Instruction: "... buy a body wash ... under $30"
- Turn 1: `search_action(keywords="cucumber aloe body wash dermatologist tested under 30")` → results listed
- Turn 2: `click_action(value="b0049tuq48")` → product page, select needed options if any
- Turn 3: `click_action(value="buy now")` → purchase succeeds **and** the agent immediately outputs:
  ```json
  {"product_id": "B0049TUQ48", "options": {}, "price": "$28.99"}
  ```
→ **PASS** (reward 1.0)

## Notes
- The skill is case‑insensitive for the `Buy Now` button because the platform sometimes capitalises the label.
- It works for any product type as long as the instruction includes a purchase request.
