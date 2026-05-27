---
description: "Enforce concise scalar decision output for conditional lab\u2011based\
  \ ordering tasks"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task4_7
  - task2_30
  - task8_19
  - task9_22
  - task8_3
  - task8_21
  - task4_4
  - task2_22
  - task9_1
  - task4_28
  update_cycle: 1
tags: []
version: 2
---

# Conditional Lab Result Ordering – Concise Decision Output

## Pattern Description
You must decide whether to place a replacement order based on the most recent lab value. The core capability is to **extract the numeric value**, compare it to the defined threshold, and then **return only the ordering decision** as a plain scalar string. The agent should never add explanatory prose, status summaries, or any surrounding text. This keeps downstream processing simple and satisfies the `verify_before_finish` skill that expects a scalar.

## When to Use This Skill
- When a task asks to *check a recent lab (e.g., potassium, magnesium, HbA1c) and conditionally order a medication or test*.
- The task description includes wording such as "If low, then order …" or "If high, then do not order …".
- The expected FINISH output is a single decision phrase like `"replacement ordered"` or `"no replacement ordered"`.

## Common Failure Patterns
- Returning a JSON‑array or list: `FINISH(["No replacement ordered"])`.
- Adding explanatory sentences: `FINISH(["Potassium level 3.9 mmol/L is above threshold; no replacement ordered."])`.
- Mixing decision with status text: `FINISH(["Replacement ordered: 40 mEq KCl IV."])` when only the decision string is required.

## Recommended Patterns
**Pattern 1: Core decision extraction**
1. Perform the GET request for the Observation (e.g., `GET /Observation?code=K&patient=...`).
2. From the returned Bundle, locate the most recent entry and extract `valueQuantity.value` as a number.
3. Compare the numeric value to the task‑specific threshold.
4. Set `decision` to one of the exact allowed strings:
   - `"replacement ordered"`
   - `"no replacement ordered"`
   - `"order pending"` (if the lab is missing or stale).
5. Call `FINISH(decision)` **without brackets, quotes inside the string, or any extra text**.

**Pattern 2: Fallback when no recent result**
- If the Bundle `total` is 0 or the latest Observation is older than the allowed window, set `decision = "no replacement ordered"` and finish.

**Pattern 3: Formatting rule**
- The FINISH argument must be a plain scalar string, **not** an array or object.
- Example of correct call: `FINISH("no replacement ordered")`.
- Example of wrong call: `FINISH(["no replacement ordered"])` or `FINISH("No replacement ordered; level is 3.9 mmol/L.")`.

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217`
2. Parse the Bundle, find the newest Observation, extract `valueQuantity.value` → `3.9`.
3. Threshold for low potassium = `3.5`. Since `3.9 >= 3.5`, set `decision = "no replacement ordered"`.
4. `FINISH("no replacement ordered")`.

**Correct output:** `FINISH("no replacement ordered")`
**Incorrect output:** `FINISH(["No recent potassium result is low; no replacement ordered."])`

## Success Indicators
- FINISH is called with a single scalar string matching one of the allowed decision phrases.
- No surrounding explanatory text appears in the FINISH argument.
- The agent does not emit an array or object as the FINISH payload.

## Failure Indicators
- FINISH receives a list, e.g., `FINISH(["no replacement ordered"])`.
- The output string contains extra words beyond the exact decision phrase.
- The agent returns a different wording such as "no potassium replacement needed" which is not one of the permitted scalars.
