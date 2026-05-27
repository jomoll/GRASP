---
description: "Append a \u201Cno replacement needed\u201D note when a recent electrolyte\
  \ result is within normal range."
name: add_no_replacement_needed_note
provenance:
  action: ADD
  epoch: 4
  fixes: 5
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task9_5
  - task8_21
  - task9_22
  - task5_7
  - task10_10
  - task5_3
  - task10_15
  - task10_18
  - task5_17
  update_cycle: 1
tags: []
version: 1
---

# Add No Replacement Needed Note for Normal Electrolyte Levels

## Pattern Description
You must decide whether a replacement order is required after fetching a recent electrolyte Observation (e.g., potassium, magnesium). If the numeric value falls inside the clinically‑accepted normal range for that test, the task expects a short explanatory note rather than an order. This skill centralises the “no replacement needed” decision so the agent does not mistakenly return only the raw value.

## When to Use This Skill
- When a task asks to *check* a recent electrolyte level and *order replacement if low* (or similar), but the retrieved value is normal.
- After a GET /Observation that returns a single entry with `valueQuantity.value` and `valueQuantity.unit` for a known electrolyte code.
- The task does **not** require any further follow‑up labs when the result is normal.

## Common Failure Patterns
- Returning only the raw lab string (e.g., `FINISH(["5.1mmol/L on 2023-11-12"])`) without a “no replacement” comment.
- Omitting the word “no replacement” or using a verbose sentence that does not match the expected short note.
- Using the wrong field (e.g., `valueString` instead of `valueQuantity.value`).

## Recommended Patterns
**Pattern 1: Extract numeric value and compare to normal range**
1. Parse the Observation bundle and locate `entry[0].resource.valueQuantity`.
2. Read `valueQuantity.value` as a number and `valueQuantity.unit`.
3. Look up the normal range for the test code (`K` → 3.5‑5.0 mmol/L, `MG` → 1.7‑2.2 mg/dL, etc.).
4. If `value` is **≥ lower** and **≤ upper**, proceed to Pattern 2.

**Pattern 2: Emit a concise “no replacement needed” FINISH**
- CORRECT: `FINISH(["Potassium 5.1 mmol/L on 2023‑11‑12 – no replacement needed."])`
- WRONG: `FINISH(["5.1mmol/L on 2023-11-12"])` (missing note)
- WRONG: Long free‑text explanations that are not a single short statement.

**Pattern 3: Fallback – if the value is outside the normal range, defer to the existing `order_service_request_if_missing_or_stale` or a separate low‑value ordering skill.**

## Example Application
**Task:** "Check patient S1796597's most recent potassium level. If low, then order replacement potassium. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=K&patient=S1796597&_sort=-date`
2. Extract `valueQuantity.value = 5.1` and `unit = "mmol/L"` from the first entry.
3. Normal range for K = 3.5‑5.0 mmol/L → 5.1 is **high**, not low.
4. Apply Pattern 2 →
   ```
   FINISH(["Potassium 5.1 mmol/L on 2023‑11‑12 – no replacement needed."])
   ```

## Success Indicators
- FINISH output contains the phrase “no replacement needed” (case‑insensitive).
- The output includes the numeric value, unit, and date in a single short string.
- No ServiceRequest POST is performed for this task.

## Failure Indicators
- FINISH output lacks the “no replacement” phrase.
- The agent issues an unnecessary ServiceRequest when the value is normal.
- The output is a raw array of strings without the explanatory note.
