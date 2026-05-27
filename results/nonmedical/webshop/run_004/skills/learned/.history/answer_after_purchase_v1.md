---
description: ensure a final answer is given immediately after clicking Buy Now
name: answer_after_purchase
provenance:
  action: ADD
  epoch: 0
  fixes: 2
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - 82
  - 14
  - 50
  - 174
  - 192
  - 88
  - 32
  - 74
  - 176
  - 4
  update_cycle: 0
tags:
- buy now
- purchase
- final answer
version: 1
---

# Answer After Purchase

## Pattern Description
When the instruction asks for a product to be bought and the agent clicks the `Buy Now` button, the task is considered complete only after the agent returns a final answer summarising the purchase. The missing step is a call to the `final_answer` tool, which causes the round to end without any response and yields a `missing_answer_call` failure.

## When to Use This Skill
- When the instruction contains a purchase request (e.g., "buy", "purchase", "add to cart") **and** the list of clickables includes `Buy Now`.
- After you have successfully executed `click_action(value="Buy Now")` and the observation still shows the product page (no further navigation buttons), you must emit a `final_answer` before the episode ends.

## Failure Pattern
- **Missing final answer** after a `click_action(value="Buy Now")`.
- The agent stops making tool calls, leaving the user with no response.
- Example logs: `click_action(value="Buy Now")` → *no subsequent `final_answer` call* → `missing_answer_call` tag.

## Action Rule
**Rule 1 (primary):**
1. Perform the normal search → open → set options → `click_action(value="Buy Now")` as usual.
2. **Immediately** after the `Buy Now` click, issue `final_answer()` with a concise confirmation (e.g., "Purchased the <product name> for $X.").

**Rule 2 (fallback):**
- If the observation after `Buy Now` shows an error (e.g., out‑of‑stock) **or** the `Buy Now` button is not present, do **not** call `final_answer`; instead, navigate back (`click_action(value="Back to Search")`) and find an alternative item.

## Verification Rule
- Confirm that the most recent action was `click_action(value="Buy Now")`.
- Verify the observation still contains the product details (price, name) and no error message.
- Ensure a `final_answer` tool call follows *before* the round limit is reached.

## Do Not
- Do not call `final_answer` before actually clicking `Buy Now`.
- Do not call `final_answer` if the `Buy Now` button was unavailable or the click resulted in an error.
- Do not omit the final answer even if the product matches all constraints.

## Example Trajectory
**WRONG trajectory:**
Instruction: "I want a black fast wireless universal charging stand under $60."
Turn 1: `search_action(keywords="black fast wireless universal charging stand under 60")` → results listed
Turn 2: `click_action(value="b0797f2v5c")` → product page with color options
Turn 3: `click_action(value="black")` → color selected
Turn 4: `click_action(value="Buy Now")` → purchase initiated
*No further tool calls* → FAIL (`missing_answer_call`)

**CORRECT trajectory:**
Instruction: "I want a black fast wireless universal charging stand under $60."
Turn 1: `search_action(keywords="black fast wireless universal charging stand under 60")` → results listed
Turn 2: `click_action(value="b0797f2v5c")` → product page with color options
Turn 3: `click_action(value="black")` → color selected
Turn 4: `click_action(value="Buy Now")` → purchase confirmed
Turn 5: `final_answer()` → "Purchased the Samsung Qi Certified Fast Charge Wireless Charger Stand (black) for $45.00."
→ PASS (reward 1.0)

## Notes
- This skill only adds a mandatory step after a successful `Buy Now` click; it does not interfere with option‑selection logic.
- It works for any product type because the trigger is the presence of the `Buy Now` action, not the product category.
