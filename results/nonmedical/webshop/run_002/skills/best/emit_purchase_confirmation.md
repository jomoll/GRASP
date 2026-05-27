---
description: "Emit a textual purchase confirmation **only** after a successful `Buy\
  \ Now` click **and** when the observation shows that the purchase has been finalized\
  \ (e.g., a thank\u2011you message or no remaining actionable clickables). This prevents\
  \ premature confirmations when a `Buy Now` button is merely present on the page\
  \ but not yet activated."
name: emit_purchase_confirmation
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 7
  regressions: 2
  triggering_sample_ids:
  - 156
  - 20
  - 190
  - 28
  - 54
  - 136
  - 154
  - 16
  - 8
  - 2
  update_cycle: 0
tags:
- purchase_confirmation
version: 1
---

## Emit Purchase Confirmation After Buying (Refined)

### Trigger Conditions
1. **Last tool call** was `click_action` with `value` matching `Buy Now` (case‑insensitive).
2. The **current observation** (the one returned *after* the `Buy Now` click) satisfies **at least one** of the following:
   - Contains a purchase‑completion phrase such as `thank you for your purchase`, `order placed`, `purchase confirmed`, `order complete`, etc.
   - Has **no remaining actionable clickables** (i.e., the `clickables` list is empty or only contains navigation like `Back to Search`).
3. All required attributes/options mentioned in the instruction are already selected (they appear as selected in the observation).
4. The displayed price is ≤ any price ceiling specified in the instruction.

If **any** of the above sub‑conditions fails, the skill does **not** emit a confirmation and the agent continues with normal tool calls.

### Primary Rule
When the trigger conditions are met, immediately output a confirmation of the form:
```
I have purchased the item "<item title>" (ID: <item id>) for $<price> as requested.
```
Do **not** issue any further `search_action` or `click_action` calls after this output.

### Fallback Rule
- If the `Buy Now` click was performed but required options are still missing, **first** select the missing options (using appropriate `click_action` calls) before re‑evaluating the trigger conditions.
- If a `Buy Now` button is present but has **not** been clicked, the skill remains inactive.

### Guard Clauses (to avoid regressions)
- **Do not** emit a confirmation simply because a `Buy Now` button appears in the list of clickables.
- **Do not** emit a confirmation if the post‑click observation still contains option selectors (e.g., size, color, quantity) that need user interaction.
- **Do not** emit a confirmation if the observation only shows navigation options (e.g., `Back to Search`) without a clear purchase‑complete message.

### Verification Steps
1. Parse the latest observation for a purchase‑complete phrase (case‑insensitive search).
2. Check `clickables` list; if it is empty or contains only non‑actionable navigation, treat as completed.
3. Ensure required options are selected and price constraint satisfied.
4. If all checks pass, produce the confirmation text and halt further tool calls.

### Example (Correct Usage)
```
Turn 1: search_action(keywords="hair elastic") → results
Turn 2: click_action(value="b018t1vznc") → product page, options selected
Turn 3: click_action(value="Buy Now") → observation includes "Thank you for your purchase!"
Turn 4: (no tool call) → output: "I have purchased the item 'Kenz Laurenz 100 Hair Elastics' (ID: b018t1vznc) for $12.98 as requested."
```

### Example (Guarded – No Confirmation Yet)
```
Turn 1: click_action(value="Buy Now") → observation shows remaining option selector "Quantity"
// Skill does nothing; agent must still select quantity before confirming.
```
