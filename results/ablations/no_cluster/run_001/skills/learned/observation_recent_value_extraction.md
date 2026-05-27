---
description: Extract the most recent Observation value, optionally limited to a time
  window, and return a numeric result or -1 if none.
name: observation_recent_value_extraction
provenance:
  action: ADD
  epoch: 1
  fixes: 3
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task4_28
  - task9_5
  - task10_27
  - task4_21
  - task3_12
  - task10_8
  - task10_13
  update_cycle: 1
tags:
- observation
- date-filter
- most-recent
- value-extraction
version: 1
---

# Observation Recent Value Extraction

## Pattern Description
You must retrieve a laboratory or vital‑sign Observation and return the **single most recent numeric value** that satisfies any time constraints specified in the task.  The pattern works for any code (e.g., "MG" for magnesium, "K" for potassium, "A1C" for hemoglobin A1c).  It centralises three reusable steps: (1) build a GET request that optionally includes a `date=ge<ISO‑timestamp>` filter, (2) sort the returned Bundle entries by `effectiveDateTime` (or `issued` when `effectiveDateTime` is absent) and pick the first entry, and (3) extract the numeric value from `valueQuantity.value` (or from a coded string when only `valueString` is present).  If no entry matches the filter, return `-1`.

## When to Use This Skill
- When a task asks for "the most recent *X* level/value" (e.g., magnesium, potassium, HbA1c).
- When the task adds a temporal qualifier such as "within the last 24 hours" or "in the past year".
- When the task expects a **single number** (or a number with a date) rather than a full Observation resource.
- When the task may require a fallback of `-1` if no qualifying Observation exists.

## Common Failure Patterns
- Omitting the `date` filter, causing old measurements to be returned.
- Selecting the first entry in the Bundle without sorting, which may not be the most recent.
- Extracting `valueString` (e.g., "118/77 mmHg") instead of the numeric component.
- Returning the whole Observation object or a list of values instead of a single number.
- Forgetting to convert units (e.g., returning mmol/L when mg/dL is required).

## Recommended Patterns
**Pattern 1: Build the GET request**
1. Identify the observation code from the task (`code=` parameter).
2. If the task specifies a time window, compute the ISO‑8601 lower bound (e.g., `now-24h`).
3. Append `date=ge<lower‑bound>` to the query string.
4. Include the patient identifier (`patient=<MRN>`).

```http
GET {base}/Observation?code={CODE}&patient={MRN}&date=ge{ISO_TIMESTAMP}
```
*If no time window is mentioned, omit the `date` parameter.*

**Pattern 2: Choose the most recent entry**
1. Parse the returned Bundle.
2. If `total == 0`, go to Pattern 3 (fallback).
3. Sort `entry.resource` objects by `effectiveDateTime` (or `issued` if the former is missing) in descending order.
4. Take the first element as the most recent Observation.

**Pattern 3: Extract the numeric value**
- Preferred: `valueQuantity.value` (already a number).
- Fallback: if only `valueString` exists, use a regex to pull the numeric part.
- Convert units if the task demands a specific unit (e.g., multiply mmol/L by 2.0 to get mg/dL for magnesium).

**Pattern 4: Return the result**
- If a value was extracted, output `FINISH([value])` (or `FINISH([value, "date"])` when the date is also required).
- If no qualifying Observation exists, output `FINISH([-1])`.

## Example Application
**Task:** "What’s the most recent magnesium level of patient S1876702 within the last 24 hours? Return the value in mg/dL, or -1 if none."

**Step‑by‑step:**
1. Compute lower bound: `2023-11-12T10:15:00Z` (now minus 24 h).
2. Issue GET:
   ```
   GET http://localhost:8080/fhir/Observation?code=MG&patient=S1876702&date=ge2023-11-12T10:15:00Z
   ```
3. Receive Bundle, sort entries by `effectiveDateTime` descending.
4. Pick first entry, extract `valueQuantity.value` (e.g., `1.6`).
5. Return:
   ```
   FINISH([1.6])
   ```

**Correct output:** `FINISH([1.6])`
**Wrong output examples:**
- Returning the whole Bundle.
- Using the first entry without sorting (could be older).
- Returning `"1.6 mg/dL"` as a string.

## Success Indicators
- The GET URL contains a `date=ge…` parameter when the task mentions a time window.
- The agent sorts the Bundle and picks the entry with the latest `effectiveDateTime`.
- The final FINISH call contains a single numeric array element (or `-1`).
- Unit conversion matches the task’s required unit.

## Failure Indicators
- The GET request lacks a `date` filter despite a time constraint.
- The agent returns the first entry without sorting, leading to an outdated value.
- The FINISH payload includes a string, an array of multiple values, or the full Observation JSON.
- The agent returns `0` or `null` instead of `-1` when no observation is found.
