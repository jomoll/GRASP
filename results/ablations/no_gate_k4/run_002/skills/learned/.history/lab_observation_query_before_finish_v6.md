---
description: Return a plain numeric lab value (or -1) with correct unit conversion
  and no extra JSON structure
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 5
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task10_24
  - task4_27
  - task9_5
  - task10_21
  - task9_11
  - task10_20
  - task4_4
  - task10_13
  update_cycle: 0
tags: []
version: 6
---

# Lab Observation Query Before Finish

## Pattern Description
When a task requires the *most recent* lab value, you must query the Observation, extract the numeric result, convert it to the unit the task expects, and return **a single scalar** (or `-1` when no recent result exists).  No arrays, strings, or explanatory text are allowed in the FINISH payload.

## When to Use This Skill
- Tasks asking for “most recent magnesium level … within last 24 hours” or similar.
- The expected answer is a single number (e.g., `1.8`) or `-1` if unavailable.
- After a GET that returns a Bundle with zero or one Observation entry.

## Common Failure Patterns
- Returning `[-1]` or `[-1]` wrapped in an array instead of the plain number `-1`.
- Returning the value together with its unit (e.g., `"1.8 mg/dL"`).
- Using the wrong field (`valueString` instead of `valueQuantity.value`).
- Failing to convert units (e.g., leaving potassium in mmol/L when the task expects mEq/L).

## Recommended Patterns
**Pattern 1: Extract numeric value**
1. Locate the first entry in the Bundle (`entry[0].resource`).
2. Read `valueQuantity.value` as a number.
3. Record `valueQuantity.unit` for conversion.

**Pattern 2: Unit conversion**
- Potassium (`K`): mmol/L → mEq/L (multiply by 1).
- Magnesium (`MG`): mg/dL is already the standard; if the source is mmol/L, multiply by 2.43.
- Apply the conversion only when the task’s description mentions a specific unit.

**Pattern 3: Return scalar**
- If the Bundle `total` is `0`, call `FINISH(-1)`.
- Otherwise call `FINISH(<converted_number>)` **without** brackets, quotes, or extra text.

## Example Application
**Task:** “What’s the most recent magnesium level of patient S2937751 within last 24 hours?”

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S2937751&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00&_sort=-date&_count=1`
2. Bundle `total = 0` → no recent result.
3. `FINISH(-1)`.

If a result existed with `valueQuantity.value = 1.8` and `unit = "mg/dL"`:
1. No conversion needed.
2. `FINISH(1.8)`.

## Success Indicators
- FINISH payload is exactly a number (e.g., `FINISH(1.8)`) or `FINISH(-1)`.
- No surrounding brackets, quotes, or explanatory text.
- The numeric value matches the lab’s `valueQuantity.value` after any required conversion.

## Failure Indicators
- FINISH contains an array (`[1.8]`) or a string (`"1.8 mg/dL"`).
- The returned number is unconverted or off by a factor.
- The agent returns `FINISH(["no replacement ordered"])` for a simple value‑query task.
