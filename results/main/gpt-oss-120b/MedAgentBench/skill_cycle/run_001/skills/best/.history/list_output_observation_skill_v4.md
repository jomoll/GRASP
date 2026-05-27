---
description: Require FINISH to return a numeric value and ISO datetime for Observation
  answers
name: list_output_observation_skill
provenance:
  action: MODIFY
  epoch: 5
  fixes: 11
  parent_version: 3
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task10_12
  - task10_24
  - task10_16
  - task10_13
  update_cycle: 0
tags: []
version: 4
---

# Observation List Output Validation

## Pattern Description
You must ensure that any FINISH response for a task that asks for the *last value* of a lab Observation returns a **JSON list** containing **exactly two elements**: the numeric result (`valueQuantity.value` as a number) and the observation timestamp (`effectiveDateTime` as an ISO‑8601 string). This prevents the agent from replying with free‑text commands such as "order_hba1c" when the task also requires the current lab result.

## When to Use This Skill
- When the task text includes a request for a lab value **and** its recording date (e.g., "What’s the last HbA1C value and when was it recorded?").
- When the task may also contain a conditional ordering clause (e.g., "If the result is older than 1 year, order a new test").
- Only for GET requests to the **Observation** resource that include a `code=` and a patient identifier.

## Common Failure Patterns
- FINISH returns a single string like `"order_hba1c"` instead of a list.
- FINISH returns a list with the wrong types (e.g., `"6.1"` as a string, or a date in a non‑ISO format).
- FINISH returns a list of the wrong length (missing value or date).

## Recommended Patterns
**Pattern 1: Extract and validate Observation fields**
1. After the Observation GET, locate the first entry in the Bundle.
2. Extract `valueQuantity.value` **as a number**. If the Observation uses `valueString`, convert to a number if possible; otherwise treat as a failure.
3. Extract `effectiveDateTime` **as an ISO‑8601 string**.
4. Verify that the value is a finite number and the date matches the pattern `YYYY‑MM‑DDThh:mm:ss+00:00`.
5. If both checks pass, prepare `FINISH([value, date])`.

**Pattern 2: Conditional ordering fallback**
1. Compare the extracted `effectiveDateTime` to the current time.
2. If the task includes a conditional cue (e.g., "greater than 1 year old", "if older than 90 days"), and the date exceeds the threshold, **first** issue the appropriate POST (e.g., ServiceRequest for a lab) **before** calling FINISH.
3. FINISH must still return the original `[value, date]` list; the order confirmation can be returned by a separate skill (e.g., `return_created_resource_confirmation`).

**Pattern 3: Formatting rule**
- The FINISH payload must be exactly `FINISH([<number>, "<ISO‑datetime>"])` with no extra whitespace or surrounding text.
- Do **not** embed explanatory text inside the list.

## Example Application
**Task:** "What’s the last HbA1C value for patient S3114648 and when was it recorded? If the result is older than 1 year, order a new test."

**Step‑by‑step:**
1. GET `.../Observation?code=A1C&patient=S3114648`.
2. From the Bundle entry, read `valueQuantity.value = 6.1` and `effectiveDateTime = "2023-10-13T22:22:00+00:00"`.
3. The date is less than 1 year old, so no order is needed.
4. Call `FINISH([6.1, "2023-10-13T22:22:00+00:00"])`.

**Correct output:** `FINISH([6.1, "2023-10-13T22:22:00+00:00"])`
**Incorrect output:** `FINISH(["6.1", "2023-10-13"] )` or `FINISH(["order_hba1c"])`

## Success Indicators
- FINISH returns a two‑element list with a numeric first element and a properly formatted ISO datetime second element.
- Any required ordering is performed **before** FINISH, and the FINISH payload still contains the value/date list.

## Failure Indicators
- FINISH payload is a single string or contains non‑numeric/non‑ISO values.
- List length is not exactly two.
- Ordering is attempted **instead of** returning the lab value/date.
