---
description: Emit a concise purchase summary immediately after a successful `Buy Now`
  click.
name: answer_after_purchase
provenance:
  action: MODIFY
  epoch: 2
  fixes: 6
  parent_version: 5
  probe_score: 7
  regressions: 2
  triggering_sample_ids:
  - 46
  - 20
  - 70
  - 134
  - 190
  - 188
  - 34
  - 40
  - 128
  - 16
  update_cycle: 1
tags:
- buy now
- purchase
- answer
- missing_answer_call
version: 6
---

# Answer After Purchase

## Pattern Description
When the instruction requires buying a product that satisfies all requested attributes and stays within the price ceiling, the agent must **immediately** output a short answer **right after** the `click_action` with `value="Buy Now"`. The answer should contain the product identifier, name, final price, and any selected option values. This ensures the round is completed with full reward (1.0) and prevents the agent from exhausting the turn budget without responding.

## When to Use This Skill
- When the observation after a `click_action` includes a **Buy Now Available Actions** block and shows product details (e.g., `product_id`, `name`, `price`, `options`).
- When the last tool call you performed in the current turn was `click_action({"value": "Buy Now"})`.
- When the instruction explicitly asks for a purchase ("buy", "purchase", "get", "need", etc.) and the agent has already selected all required options.

## Failure Pattern
- **Missing answer after purchase** – the agent clicks `Buy Now` but does not emit the final answer, leading to a *missing_answer_call* tag.
- **Answer emitted before clicking `Buy Now`**, causing an incomplete purchase and partial reward.
- **Answer emitted with the wrong format** (e.g., plain text instead of the required JSON object).

## Action Rule
**Rule 1: Primary behavior**
1. After you execute `click_action({"value": "Buy Now"})`, inspect the observation.
2. If the observation contains a JSON block with keys `product_id`, `name`, `price`, and possibly `options`, **immediately** output a JSON answer of the form:
```json
{ "product_id": "<id>", "name": "<name>", "price": "<price>", "options": { ... } }
```
   - Use the exact values shown in the observation; do not modify them.
3. End the episode – do not issue any further tool calls.

**Rule 2: Fallback**
- If the observation after `Buy Now` does **not** contain the expected product fields (e.g., an error page), first issue `click_action({"value": "< Prev>"})` or `click_action({"value": "Back to Search"})` to recover, then retry the purchase and apply Rule 1.

## Verification Rule
- Confirm that the observation after `Buy Now` includes a `product_id` field.
- Verify the price is ≤ the ceiling stated in the instruction.
- Ensure all requested options (color, size, count, etc.) appear in the `options` object.
- The output must be a **single JSON object** on one line, matching the schema above.

## Do Not
- Do not wait for another `search_action` or `click_action` after a `Buy Now` click.
- Do not output any explanatory text, just the JSON answer.
- Do not emit the answer if you have not yet clicked `Buy Now`.
- Do not use option values that are not present in the current `clickables` list.

## Example Trajectory
**WRONG trajectory** (fails to answer after purchase):
```
Instruction: "i need a large sized coat with long sleeves, and price lower than 70 dollars"
Turn 1: Think → search_action(keywords="large coat long sleeves under $70")
Observation: ... (list of results) ...
Turn 2: Think → click_action(value="b09mmw35lf")
Observation: ... (product page with size options) ...
Turn 3: Think → click_action(value="large")
Observation: ... (size selected) ...
Turn 4: Think → click_action(value="Buy Now")
Observation: {"product_id":"b09mmw35lf", "name":"Coats for Women...", "price":"$28.28", ...}
Turn 5: Think → (no answer emitted) → task ends → FAIL (missing_answer_call)
```

**CORRECT trajectory** (emits answer immediately after purchase):
```
Instruction: "i need a large sized coat with long sleeves, and price lower than 70 dollars"
Turn 1: Think → search_action(keywords="large coat long sleeves under $70")
Observation: ... (list of results) ...
Turn 2: Think → click_action(value="b09mmw35lf")
Observation: ... (product page with size options) ...
Turn 3: Think → click_action(value="large")
Observation: ... (size selected) ...
Turn 4: Think → click_action(value="Buy Now")
Observation: {"product_id":"b09mmw35lf", "name":"Coats for Women...", "price":"$28.28", "options":{ "size":"large" }}
Turn 5: Think → **Answer**
Output: {"product_id":"b09mmw35lf","name":"Coats for Women...","price":"$28.28","options":{"size":"large"}}
→ PASS (reward 1.0)
```

## Notes
- The skill is safe because it only adds a single answer step after a deterministic `Buy Now` click; it never consumes extra search rounds.
- It works for any product type as long as the observation follows the standard product JSON format used by WebShop.
