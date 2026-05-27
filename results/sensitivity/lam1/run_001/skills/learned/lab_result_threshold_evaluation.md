---
description: "Extract lab value and date, order new test if result >1\u202Fyear old,\
  \ return both"
name: lab_result_threshold_evaluation
provenance:
  action: MODIFY
  epoch: 2
  fixes: 6
  parent_version: 2
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task8_26
  - task5_19
  - task5_3
  - task10_13
  - task9_1
  - task9_20
  - task8_5
  - task9_22
  update_cycle: 1
tags: []
version: 3
---

# Lab Result Extraction and Recency Evaluation

## Pattern Description
You must reliably extract the most recent laboratory observation value and its timestamp, then decide whether a new test is needed based on recency. This pattern applies to any task that requests the *last* value of a lab (e.g., HbA1c, potassium, magnesium) and may include a conditional ordering clause such as “if the result is older than 1 year, order a new test.”

## When to Use This Skill
- The task description contains phrases like “last *X* value”, “most recent *X* level”, or “what’s the *X* result”.
- The task mentions a recency condition (e.g., “if the result date is greater than 1 year old, order …”).
- An `GET /Observation` request for the relevant LOINC/code has been issued but no value has yet been extracted.

## Common Failure Patterns
- Returning `-1` or an empty array without first extracting `valueQuantity.value` (or `valueString` for non‑numeric labs) and `effectiveDateTime`.
- Ordering a new `ServiceRequest` **before** extracting the existing result, causing the final `FINISH` payload to miss the value/date.
- Using the wrong field (`valueString` for numeric labs) or forgetting to convert the date to a comparable timestamp.

## Recommended Patterns
**Pattern 1: Extract the latest observation**
1. Inspect the `Bundle` response from the `GET /Observation` call.
2. Ensure `total >= 1` and that the first entry’s `resource` is an `Observation`.
3. Extract the numeric result:
   - Prefer `valueQuantity.value` (numeric) → `lab_value`.
   - If `valueQuantity` is absent, fall back to `valueString` and attempt numeric conversion.
4. Extract the timestamp from `effectiveDateTime` → `lab_date` (ISO‑8601 string).
5. Store both for later use.

**Pattern 2: Recency check and optional ordering**
1. Parse `lab_date` and the current time supplied in the task context.
2. Compute the difference in days.
3. If `difference > 365` days **or** `total == 0` (no recent result), create a `ServiceRequest` for the appropriate LOINC ordering code.
   - Use the ordering LOINC code supplied in the task (e.g., `4548-4` for HbA1c).
   - Include a note explaining the recency trigger.
4. Regardless of ordering, prepare the final answer.

**Pattern 3: Formatting the final output**
- If a lab value was extracted, `FINISH([lab_value, lab_date])`.
- If no value exists, `FINISH([-1])` (or a custom message if the task demands it).
- Do **not** embed free‑text explanations inside the array; keep the payload strictly typed.

## Example Application
**Task:** "What’s the last HbA1C value for patient S1311412 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET {api_base}/Observation?code=A1C&patient=Patient/S1311412&_sort=-date&_count=1`
2. Response Bundle contains an Observation with:
   - `valueQuantity.value = 5.9`
   - `effectiveDateTime = "2023-11-12T06:19:00+00:00"`
3. Parse current context time `2023-11-13T10:15:00+00:00` → difference = 1 day (<365). No ordering needed.
4. `FINISH([5.9, "2023-11-12T06:19:00+00:00"])`

**If the date had been `2022-09-01T08:00:00+00:00`** (difference >365):
1. After extraction, create a `POST /ServiceRequest` with LOINC `4548-4` and a note about recency.
2. Still return the extracted value/date: `FINISH([value, date])`.

## Success Indicators
- The agent extracts a numeric `lab_value` and a valid ISO‑8601 `lab_date` before any ordering.
- When the result is older than 1 year (or missing), a `POST /ServiceRequest` is issued with the correct ordering code.
- The final `FINISH` payload is a JSON array containing the value and date (or `-1` when no value).

## Failure Indicators
- `FINISH` contains `-1` or an empty array while a recent observation exists in the Bundle.
- The agent posts a `ServiceRequest` **without** first extracting the existing value/date.
- The output array includes free‑text strings or extra fields beyond the required `[value, date]`.
