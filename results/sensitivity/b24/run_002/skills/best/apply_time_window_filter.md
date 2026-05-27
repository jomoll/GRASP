---
description: "Ensure Observation searches are limited to the last 24\u202Fhours using\
  \ a date filter."
name: apply_time_window_filter
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task1_23
  - task5_19
  - task10_18
  - task10_10
  - task10_13
  - task10_12
  - task9_8
  update_cycle: 1
tags:
- observation
- date_filter
- time_window
version: 1
---

# apply_time_window_filter

## Pattern Description
You must always restrict a search for recent laboratory or vital‑sign values to the last 24 hours.  The FHIR `Observation` search supports a `date` parameter that can be used with a comparison prefix (`ge` for "greater‑or‑equal").  By adding this filter you avoid using stale measurements that fall outside the required time window, which is a common source of incorrect clinical decisions.

## When to Use This Skill
- When a task asks for the *most recent* value of a lab or vital sign **within the last 24 hours** (e.g., magnesium, potassium, HbA1c, blood pressure).
- When the task explicitly says *"if no value has been recorded in the last 24 hours, do nothing"*.
- When constructing a GET request to `/Observation` with a `code` and `patient` parameter.

## Common Failure Patterns
- Omitting the `date` parameter entirely, causing the query to return all historic values.
- Using the wrong prefix (`gt` instead of `ge`) and accidentally excluding a value that occurred exactly 24 hours ago.
- Building the timestamp with the wrong timezone or format, e.g., missing the trailing `Z` or using a local offset.
- Adding the filter after the request has already been sent (i.e., forgetting to include it in the URL).

## Recommended Patterns
**Pattern 1: Build a correct 24‑hour date filter**
1. Parse the current time from the task context (e.g., `2023-11-13T10:15:00+00:00`).
2. Subtract 24 hours to obtain the lower bound timestamp.
3. Format the timestamp exactly as ISO‑8601 with timezone, e.g., `2023-11-12T10:15:00+00:00`.
4. Append `&date=ge<timestamp>` to the Observation GET URL.

   **CORRECT**: `GET /fhir/Observation?code=MG&patient=S1234567&date=ge2023-11-12T10:15:00+00:00`
   **WRONG**: `GET /fhir/Observation?code=MG&patient=S1234567` (no date filter)

**Pattern 2: Verify the filter worked**
- After receiving the Bundle, check the `total` field. If `total == 0`, you have correctly determined that no recent measurement exists.
- If `total > 0`, extract the most recent entry by sorting on `effectiveDateTime` (or `issued` if the former is missing).

**Pattern 3: Decision logic based on filtered result**
- If a recent value is present, compare it to the clinical threshold defined in the task.
- If the value is low, construct the appropriate `MedicationRequest` (or other order) and POST it.
- If no recent value, **do not** place any order and finish with a clear message.

## Example Application
**Task:** "Check patient S3057899's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step‑by‑step:**
1. Extract current time from the task context: `2023-11-13T10:15:00+00:00`.
2. Compute lower bound: `2023-11-12T10:15:00+00:00`.
3. Issue GET:
   ```
   GET http://localhost:8080/fhir/Observation?code=MG&patient=S3057899&date=ge2023-11-12T10:15:00+00:00
   ```
4. If the response Bundle `total` is 0 → FINISH(["No magnesium level recorded in the last 24 hours; no replacement ordered."])
5. If `total` > 0, locate the entry with the greatest `effectiveDateTime`.
6. Extract `valueQuantity.value` (mg/dL) and compare to the low‑threshold (e.g., <1.5 mg/dL).
7. If low, POST a `MedicationRequest` for IV magnesium using the provided NDC and dosing instructions, then FINISH(["Magnesium replacement ordered."]).

**Correct output when no recent value:**
```
FINISH(["No magnesium level recorded in the last 24 hours; no replacement ordered."])
```
**Correct output when low value found:**
```
FINISH(["Magnesium replacement ordered."])
```

## Success Indicators
- Every Observation GET for a recent‑value task includes `&date=ge<timestamp>`.
- The agent correctly reports "no recent measurement" when the Bundle `total` is 0.
- When a recent low value exists, the agent creates and POSTs the appropriate order.

## Failure Indicators
- Observation GET URLs lack a `date` parameter.
- The agent reports a value that is older than 24 hours.
- The agent orders medication even when the Bundle `total` is 0.
- Timestamp formatting errors cause the server to reject the request or return an empty set incorrectly.
