---
description: Validate that Observation values include the expected unit and return
  the value with that unit, **but only when the task explicitly requests a plain numeric
  answer with a unit** (e.g., it says "answer should be a single number in mg/dL"
  or similar). This guard prevents the skill from interfering with tasks that involve
  ordering, scheduling, or any narrative response.
name: observation_quantity_unit_validation
provenance:
  action: ADD
  epoch: 2
  fixes: 7
  probe_score: 6
  regressions: 2
  triggering_sample_ids:
  - task10_8
  - task4_15
  - task9_28
  - task10_17
  - task2_14
  - task9_3
  - task9_8
  - task2_1
  - task2_28
  - task9_11
  update_cycle: 0
tags: []
version: 1
---

## Observation Quantity Unit Validation (Guarded)

### When to Activate
- Activate **only** if the task description contains a clear request for a numeric lab value **and** mentions the desired unit, such as phrases like:
  - "answer should be a single number in *unit*"
  - "provide the value in *unit*"
  - "return the most recent *lab* level as a number with unit"
- Do **not** activate if the task includes any of the following intents:
  - Ordering medication or supplies
  - Scheduling a future observation
  - Pairing an order with another procedure
  - Any narrative explanation beyond the raw value
- This guard ensures the skill does not interfere with complex clinical workflow tasks.

### Core Extraction and Unit Verification (same as original)
1. `GET {base}/Observation?code={LAB_CODE}&patient={MRN}`.
2. From the returned Bundle, locate the entry with the most recent `effectiveDateTime` that satisfies any required time window.
3. Inspect `entry.resource.valueQuantity`:
   - `valueQuantity.value` → numeric value.
   - `valueQuantity.unit` → unit string.
4. Compare the observed unit to the expected unit supplied in the task context.
   - If they match, proceed.
   - If they differ but are a known convertible pair (e.g., `mmol/L` → `mg/dL` for magnesium), apply the conversion factor and replace the unit with the expected one.
5. Return `FINISH([numeric_value, "expected_unit"])`.

### Fallback when No Recent Measurement
- If the Bundle `total` is 0 **or** no entry satisfies the time filter, answer `FINISH([-1])`.

### Formatting Rule
- The final JSON array must contain a **number** (not a string) for the value and a **string** for the unit. Do not embed the unit inside the number or return a concatenated string.

### Example (still valid)
**Task:** "What’s the most recent magnesium level of patient S3057899 within last 24 hours? The answer should be a single number converted to a unit of mg/dL."
- Follow steps 1‑5 and return `FINISH([2.2, "mg/dL"])`.

### Guard Implementation (pseudo‑code for the skill engine)
```
if not (task_description matches /answer.*(unit|mg\/dL|mmol\/L|g\/dL)/i):
    skip this skill
if task_description matches /order|schedule|pair|next day|administer|prescribe/i:
    skip this skill
# otherwise proceed with the original extraction logic
```

This revised version retains the original functionality for pure numeric‑unit queries while preventing regressions on tasks that require richer clinical actions.
