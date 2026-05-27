---
description: Extract the latest lab Observation value and date, then order a repeat
  test if the result is older than a threshold.
name: lab_observation_extraction_and_ordering
provenance:
  action: ADD
  epoch: 3
  fixes: 9
  probe_score: 5
  regressions: 3
  triggering_sample_ids:
  - task10_27
  - task9_5
  - task2_25
  - task10_20
  - task10_16
  - task10_15
  - task9_8
  - task5_3
  - task9_20
  - task9_27
  update_cycle: 1
tags: []
version: 1
---

# Lab Observation Extraction and Conditional Ordering

## Pattern Description
You must reliably pull the most recent lab result for a given LOINC code from a FHIR Observation bundle, normalize the numeric value, and return both the value **and** the recording date. If the task also specifies a freshness requirement (e.g., "order a new test if the result is > 1 year old"), you must evaluate the extracted date and, when the condition is met, create an appropriate `ServiceRequest` before finishing.

This pattern is reusable for any single‑value lab (HbA1c, potassium, magnesium, etc.) where the answer requires both the measurement and its timestamp, and where a conditional re‑order may be required.

## When to Use This Skill
- The instruction asks for "the last *X* value" **and** the date it was recorded.
- The instruction adds a conditional clause such as "if the result is older than *N* days/years, order a new *X* test."
- The GET request you performed is `Observation?code=<LOINC>&patient=Patient/<MRN>` and the response is a `Bundle`.
- The Observation may store the result in `valueQuantity.value` (numeric) **or** `valueString` (e.g., "5.6 mmol/L").
- The timestamp may be in `effectiveDateTime` or `issued`.

## Common Failure Patterns
- Returning the placeholder `FINISH([-1])` because no extraction logic exists.
- Using the wrong field (`valueString` when a numeric value is required) and returning a string.
- Ignoring the timestamp and never performing the conditional order.
- Posting a `ServiceRequest` unconditionally, even when the existing result is recent.
- Forgetting to convert units (e.g., mg/dL vs mmol/L) when the task expects a specific unit.

## Recommended Patterns
**Pattern 1: Locate the most recent Observation**
1. Inspect the bundle `entry` array. If `total == 0`, treat as "no result" and set `value = -1`.
2. Otherwise, sort entries by `resource.effectiveDateTime` (fallback to `resource.issued`) descending.
3. Pick the first entry – this is the latest result.

**Pattern 2: Extract and normalize the numeric value**
- If `resource.valueQuantity` exists, use `resource.valueQuantity.value` (already numeric).
- If only `resource.valueString` exists, strip non‑numeric characters and parse the number.
- Apply unit conversion if the task mentions a required unit (use the existing `format_quantity_with_unit` skill).

**Pattern 3: Extract the result date**
- Prefer `resource.effectiveDateTime`; if missing, use `resource.issued`.
- Keep the ISO‑8601 string for the final answer.

**Pattern 4: Conditional ordering**
1. Parse the extracted date into a datetime.
2. Compute the age relative to the current context time supplied in the task.
3. If the age exceeds the threshold (e.g., 1 year), build a `ServiceRequest`:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC>", "display": "<Test Name>" }] },
     "authoredOn": "<CURRENT_TIME>",
     "status": "active",
     "intent": "order",
     "priority": "routine",
     "subject": { "reference": "Patient/<MRN>" }
   }
   ```
4. POST the request **only** when the condition is true.

**Pattern 5: Finish the task**
- If a value was found, return `FINISH([<numeric_value>, "<date>"])`.
- If no value was found, return `FINISH([-1])` (or a task‑specific message).
- Do **not** include any free‑text explanation; the array must match the expected type.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6550627 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=Patient/S6550627`
2. Bundle `total = 1`; sort (only one entry) → latest Observation.
3. Extract `valueQuantity.value = 7.2` (numeric) and `effectiveDateTime = "2022-09-10T08:30:00+00:00"`.
4. Compare date to current time `2023-11-13T10:15:00+00:00`; age = 1 year + 34 days → exceeds 1 year.
5. Build and `POST` a `ServiceRequest` with LOINC `4548-4` (HbA1c).
6. `FINISH([7.2, "2022-09-10T08:30:00+00:00"])`.

**Correct output:** `FINISH([7.2, "2022-09-10T08:30:00+00:00"])`
**Wrong output:** `FINISH([-1])` or `FINISH(["7.2% on 2022-09-10"])`.

## Success Indicators
- The final `FINISH` call contains a numeric value (or `-1`) and, when required, an ISO‑8601 date string.
- A `ServiceRequest` is posted **only** when the result is older than the specified threshold.
- No placeholder `[-1]` is returned when a valid Observation exists.

## Failure Indicators
- `FINISH([-1])` despite a non‑empty Observation bundle.
- The returned array contains a string instead of a number.
- A `ServiceRequest` is posted regardless of the age check.
- The date field is missing or malformed in the final answer.
