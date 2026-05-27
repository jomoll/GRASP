---
description: Immediately issue a final answer after a successful `Buy Now` click
name: answer_after_purchase
provenance:
  action: MODIFY
  epoch: 0
  fixes: 2
  parent_version: 1
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 148
  - 58
  - 28
  - 92
  - 66
  - 128
  - 126
  - 24
  - 170
  - 10
  update_cycle: 1
tags:
- buy now
- purchase
- final answer
version: 2
---

# Answer After Purchase

## Pattern Description
When the instruction requires buying a product, the agent must **click the `Buy Now` button** and then **provide the final answer in the very next turn**. The answer should summarise the purchased item (its ID, selected options and price) and no further tool calls are allowed. This guarantees a full 1.0 reward because the task is considered completed as soon as the purchase is confirmed.

## When to Use This Skill
- When the observation shows a clickable `Buy Now` button and you have already selected all required options (size, color, quantity, etc.).
- When you have just executed `click_action({"value": "Buy Now"})` and the observation still contains the product page (no new search results are shown).

## Failure Pattern
- **Missing final answer**: after `click_action(...{"value": "Buy Now"})` the agent continues searching or clicking other buttons, eventually hitting the task limit.
- **Calling another tool**: `click_action` or `search_action` after `Buy Now` leads to partial reward.
- **No output at all**: the round ends without a `final_answer` response.

## Action Rule
**Rule 1: Primary behavior**
1. Detect that the last tool call was `click_action` with `value` equal to `Buy Now`.
2. In the next turn, **do not call any tool**. Instead, output a `final_answer` containing:
   - The product identifier (e.g., `B08ZJVJ7FZ`).
   - Any options you selected (size, color, quantity, etc.).
   - The final price (as shown in the observation).
3. End the episode.

**Rule 2: Fallback**
- If the observation after the `Buy Now` click does **not** contain a purchase confirmation (e.g., the button disappeared or an error is shown), first verify the purchase by checking for a price line or a "Added to cart" message. If the purchase failed, you may retry the `Buy Now` click, but **still** must answer immediately after a successful click.

## Verification Rule
- Confirm that the most recent observation still displays the product details and a price line (e.g., `$34.99`).
- Ensure the last action was `click_action` with `value` exactly `Buy Now`.
- No further `search_action` or `click_action` calls appear after this turn.

## Do Not
- Do not perform any additional `search_action` or `click_action` after clicking `Buy Now`.
- Do not output anything other than a `final_answer` (no explanatory text, no extra tool calls).
- Do not ignore the `Buy Now` click and loop back to pagination.

## Example Trajectory
**WRONG trajectory:**
Instruction: "Buy a blue USB‑C cable under $50."
```
Turn 1: Think → search_action(keywords="blue USB‑C cable under 50")
Turn 2: Act  → click_action(value="b09mv8b4pk")   # open item page
Turn 3: Think → click_action(value="Buy Now")   # purchase
Turn 4: Act  → search_action(keywords="blue USB‑C cable")   # unnecessary extra step → FAIL (task limit reached, no final answer)
```

**CORRECT trajectory:**
Instruction: "Buy a blue USB‑C cable under $50."
```
Turn 1: Think → search_action(keywords="blue USB‑C cable under 50")
Turn 2: Act  → click_action(value="b09mv8b4pk")   # open item page
Turn 3: Think → click_action(value="Buy Now")   # purchase
Turn 4: Act  → final_answer({"product_id": "b09mv8b4pk", "options": {}, "price": "$34.99"})   # immediate answer → PASS (reward 1.0)
```

## Notes
- This skill is a **constraint**: it restricts the workflow after a purchase rather than adding extra steps.
- It works for any product type because the trigger is the literal `Buy Now` click, which is present in all WebShop tasks that require a purchase.
