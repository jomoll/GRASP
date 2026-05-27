---
description: "Emit final answer immediately after a successful Buy\u202FNow click"
name: answer_after_purchase
provenance:
  action: MODIFY
  epoch: 1
  fixes: 3
  parent_version: 3
  probe_score: 4
  regressions: 4
  triggering_sample_ids:
  - 140
  - 28
  - 60
  - 48
  - 114
  - 84
  - 162
  - 148
  - 50
  - 34
  update_cycle: 1
tags: []
version: 4
---

# Emit Answer After Purchase

## Pattern Description
When the instruction requires buying a product, the agent must finish the episode by outputting the purchase summary **right after** it clicks the `Buy Now` button. The answer should contain the product ID, any selected options, and the final price. Skipping this final answer causes a *missing_answer_call* failure, even though the purchase itself succeeded.

## When to Use This Skill
- When the available actions list includes a clickable named `Buy Now` (case‑insensitive) and the previous tool call was `click_action` with `value` equal to `Buy Now` or `buy now`.
- When the observation after the click shows product details (e.g., `product_id`, `options`, `price`).
- Bad: "When the task is any shopping request" (too broad).

## Failure Pattern
- **Missing answer after purchase** – The agent clicks `Buy Now` but then does not produce a final JSON answer, leading to `missing_answer_call`.
- **Clicking an unavailable value** – The agent attempts `click_action` with a value not in the `clickables` list, so the click is ignored and no purchase occurs.

## Action Rule
**Rule 1: primary behavior**
1. Detect that the last tool call was `click_action` with `value` matching `/^buy now$/i`.
2. Verify that the current observation contains a `product_id` field (or a line starting with `product_id`).
3. Immediately emit a final answer JSON of the form:
   ```json
   {"product_id": "<ID>", "options": {<selected options>}, "price": "<price>"}
   ```
   using the information already present in the observation.

**Rule 2: fallback**
- If the observation after `Buy Now` does **not** contain a `product_id` (e.g., the click was ignored), first issue a `click_action` with a valid value from the `clickables` list (e.g., `Buy Now` again) before emitting the answer.

## Verification Rule
- Confirm that the last observation includes a line like `product_id: "B..."` or a JSON snippet with `"product_id"`.
- Ensure that any required option selections have already been made (they appear in the observation as selected values).
- Only output the answer after these conditions are satisfied; do not wait for another round.

## Do Not
- Do not wait for the user to ask for the result; the answer must be automatic.
- Do not emit the answer before the `Buy Now` click has been observed.
- Do not click a value that is not present in the `clickables` list.
- Do not produce any additional tool calls after the answer.

## Example Trajectory
**WRONG trajectory:**
Instruction: "Buy a women's sneaker size 6.5 under $220."
Turn 1: `search_action(keywords="women's sneakers size 6.5")` → results listed
Turn 2: `click_action(value="b08zm9jc3h")` → item page with size options
Turn 3: `click_action(value="6.5 women | 5 men")` → size selected
Turn 4: `click_action(value="buy now")` → purchase succeeds, observation shows `product_id: "B08ZM9JC3H"`
Turn 5: **No answer emitted** → FAIL (`missing_answer_call`)

**CORRECT trajectory:**
Instruction: "Buy a women's sneaker size 6.5 under $220."
Turn 1: `search_action(keywords="women's sneakers size 6.5")` → results listed
Turn 2: `click_action(value="b08zm9jc3h")` → item page with size options
Turn 3: `click_action(value="6.5 women | 5 men")` → size selected
Turn 4: `click_action(value="buy now")` → observation contains `product_id: "B08ZM9JC3H"`, `price: "$64.90"`
Turn 5: **Agent emits** `{"product_id": "B08ZM9JC3H", "options": {"size": "6.5"}, "price": "$64.90"}` → PASS (reward 1.0)

## Notes
- This skill only fires on the exact `Buy Now` click; other clicks (e.g., `Add to Cart`) are unaffected.
- The emitted JSON must follow the format used in successful examples so downstream evaluation can parse it.
