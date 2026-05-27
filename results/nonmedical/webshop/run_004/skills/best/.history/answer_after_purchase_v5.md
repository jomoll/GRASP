---
description: Emit final answer immediately after a successful `buy now` click
name: answer_after_purchase
provenance:
  action: MODIFY
  epoch: 2
  fixes: 3
  parent_version: 4
  probe_score: 6
  regressions: 4
  triggering_sample_ids:
  - 36
  - 156
  - 14
  - 172
  - 140
  - 66
  - 122
  - 148
  - 4
  - 116
  update_cycle: 0
tags: []
version: 5
---

# Emit Answer Immediately After Successful Buy Now

## Pattern Description
When the user’s instruction has been satisfied and the agent clicks the `buy now` button, the episode is complete.  The only remaining step is to return a concise summary of the purchased product (product id, name, price, and any selected options).  Emitting this answer right after the `click_action` with value `buy now` guarantees a full reward (1.0) because the required item, all requested attributes, and the price ceiling have already been verified.

## When to Use This Skill
- When the observation after a tool call lists **clickables** that include `buy now` **and** the product page shows the final price/options (e.g., `price: $24.0`, selected color/size listed).
- When the last executed tool was `click_action({"value": "buy now"})`.
- When no further clickables other than `back to search` or `buy now` remain.

## Failure Pattern
- **Missing answer after `buy now`** – the agent clicks `buy now` but does not emit the final answer, causing `missing_answer_call`.
- **Waiting for another tool call after `buy now`** – the agent loops or issues a `search_action` unnecessarily.
- **Returning an empty JSON or a non‑answer message after purchase**.

## Action Rule
**Rule 1: Primary behavior**
1. Detect that the most recent tool call was `click_action` with `value` exactly `"buy now"`.
2. From the latest observation, extract the product details:
   - `product_id` (e.g., `b09bc7tr8p`)
   - `name` (text after the id)
   - `price` (the `$XX` string)
   - any selected options that were clicked earlier (color, size, quantity, etc.).
3. Immediately output a JSON answer of the form:
```json
{ "product_id": "<id>", "name": "<name>", "price": "<price>", "options": {"color": "<color>", "size": "<size>", ...} }
```
   Include only the options that were explicitly selected.

**Rule 2: Fallback**
- If the observation after `buy now` does **not** contain a price line or product name (unlikely but possible), first issue a `click_action` with value `"description"` (or the only available info button) and then emit the answer after that second click.

## Verification Rule
- Confirm that the last tool call was `click_action({"value": "buy now"})`.
- Confirm that the observation contains a line starting with `Price:` or a `$` price and the product name appears.
- Ensure no further clickables other than navigation (e.g., `back to search`) are needed to satisfy the instruction.

## Do Not
- Do not issue another `search_action` after clicking `buy now`.
- Do not wait for the user to prompt again before answering.
- Do not output anything other than the final JSON answer.
- Do not click any button whose value is not present in the current `clickables` list.

## Example Trajectory
**WRONG trajectory:**
Instruction: "i'm looking for a single pack of old style, brown hair dye, and price lower than 40.00 dollars"
Turn 1: `search_action({"keywords": "old style brown hair dye single pack under $40"})` → results listed
Turn 2: `click_action({"value": "b09bc7tr8p"})` → item page with color options
Turn 3: `click_action({"value": "buy now"})` → purchase performed **but no answer emitted**
→ **FAIL** (missing answer call)

**CORRECT trajectory:**
Instruction: same as above
Turn 1: `search_action({"keywords": "old style brown hair dye single pack under $40"})` → results listed
Turn 2: `click_action({"value": "b09bc7tr8p"})` → item page, select `brown` if needed
Turn 3: `click_action({"value": "buy now"})` → purchase performed
Turn 4: **Agent emits answer**
```json
{ "product_id": "b09bc7tr8p", "name": "Root Touch Up Semi-Permanent Root Hair Coloring", "price": "$24.99", "options": {"color": "brown"} }
```
→ **PASS** (reward 1.0)

## Notes
- This skill is purely reactive to the `buy now` click; it does not alter search or option‑selection logic.
- It works for any product type because the trigger (`click_action` value `buy now`) is universal across WebShop tasks.
