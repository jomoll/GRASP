---
description: Extract numeric lab value and timestamp, return [-1] when missing (no
  placeholder string)
name: observation_value_extraction
provenance:
  action: MODIFY
  epoch: 3
  fixes: 6
  parent_version: 2
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task9_5
  - task10_21
  - task9_11
  - task10_20
  - task10_13
  - task9_22
  - task4_20
  - task5_3
  - task9_27
  update_cycle: 0
tags: []
version: 3
---

# observation_value_extraction

## Pattern Description
You must reliably pull a numeric result and its recording time from an Observation bundle. The skill works for any lab identified by a LOINC code (or other code) and returns a two‑element array **[value, timestamp]** when a valid result exists. If the bundle contains no entries *or* the entry lacks a usable numeric value, you must return a **single‑element array `[-1]`** – never a placeholder string.

## When to Use This Skill
- When a task asks for "the last *X* value" and provides a LOINC or code to query Observations.
- When the answer format is defined as `[numeric_value, "ISO‑8601 timestamp"]` or `[-1]` for missing data.
- Triggered immediately after a `GET /Observation?...` response is received.

## Common Failure Patterns
- Returning `[-1, ""]` (two‑element placeholder) instead of `[-1]`.
- Extracting the value from `valueString` without converting to a number.
- Using `issued` when `effectiveDateTime` is the correct timestamp field.
- Selecting the first entry instead of the most recent (`effectiveDateTime` descending).

## Recommended Patterns
**Pattern 1: Primary extraction**
1. Verify the bundle `total` > 0. If not, go to fallback (Pattern 2).
2. Sort `entry` objects by `resource.effectiveDateTime` (or `issued` if `effectiveDateTime` missing) descending.
3. Take the first entry.
4. Extract the numeric value:
   - Prefer `resource.valueQuantity.value` (number).
   - If absent, try parsing `resource.valueString` for a number.
5. Extract the timestamp from `resource.effectiveDateTime` (or `issued`).
6. **Return** `[value, timestamp]`.

**Pattern 2: Missing or invalid result fallback**
1. If the bundle is empty **or** the selected entry lacks a numeric value, **return** `[-1]`.
2. Do **not** include a second element (no empty string).

**Pattern 3: Formatting check**
- Ensure the numeric value is a plain JSON number, not a string.
- Ensure the timestamp is an ISO‑8601 string.
- Do not wrap the result in additional arrays or objects.

## Example Application
**Task:** "What’s the last HbA1c value for patient S123456 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S123456`
2. Bundle `total` = 3 → proceed.
3. Sort entries by `effectiveDateTime`; most recent has `effectiveDateTime = "2023-10-01T09:30:00+00:00"`.
4. Extract `valueQuantity.value = 5.7`.
5. Return `FINISH([5.7, "2023-10-01T09:30:00+00:00"])`.

**When no result exists:**
1. Bundle `total` = 0.
2. Return `FINISH([-1])`.

## Success Indicators
- The FINISH payload is either `[number, "timestamp"]` or `[-1]`.
- No empty strings appear in the array.
- The numeric value matches the `valueQuantity.value` from the most recent Observation.

## Failure Indicators
- FINISH payload contains two elements where the first is `-1` (e.g., `[-1, ""]`).
- The timestamp is missing or not ISO‑8601.
- The value is a string or includes units.
- The agent selects an older Observation when a newer one exists.
