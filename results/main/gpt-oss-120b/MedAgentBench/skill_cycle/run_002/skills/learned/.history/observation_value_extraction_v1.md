---
description: Extract numeric lab value and date from an Observation bundle, returning
  -1 only when no valid result exists.
name: observation_value_extraction
provenance:
  action: ADD
  epoch: 0
  fixes: 13
  probe_score: 12
  regressions: 1
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task3_14
  - task4_11
  update_cycle: 0
tags:
- observation
- extraction
- value_parsing
- fallback
version: 1
---

# Observation Value Extraction

## Pattern Description
You must reliably pull the most recent numeric result from a FHIR Observation search bundle. The skill works for any lab or vital sign where the value is stored in `valueQuantity.value` (or `valueString` for non‑numeric results) and the timestamp is in `effectiveDateTime`. If the bundle contains no entries, you return the placeholder `-1` (or `"-1"` inside a JSON array) as the task specifies. This pattern prevents the agent from blindly returning the placeholder without first inspecting the response.

## When to Use This Skill
- When a task asks for the latest value of a lab test or vital sign (e.g., HbA1c, magnesium, potassium) and the query is a `GET .../Observation?...`.
- When the task also requires the date the observation was recorded, or a decision based on the age of the result.
- When the response is a FHIR `Bundle` that may contain zero, one, or many `Observation` entries.

## Common Failure Patterns
- Returning `-1` immediately without checking `bundle.total` or `bundle.entry`.
- Extracting the wrong field (e.g., using `valueString` for a numeric LOINC that stores `valueQuantity`).
- Ignoring the `effectiveDateTime` and therefore unable to apply “older than 1 year” logic.
- Concatenating the numeric value with its unit (e.g., `"5.6%"`) instead of returning a pure number.

## Recommended Patterns
**Pattern 1: Core extraction workflow**
1. Parse the JSON response as a FHIR Bundle.
2. If `bundle.total == 0` **or** `bundle.entry` is missing/empty → `FINISH(["-1"])`.
3. Otherwise, sort `bundle.entry` by `resource.effectiveDateTime` descending (most recent first).
4. From the first entry, read:
   - `value = resource.valueQuantity.value` **or** `resource.valueString` if `valueQuantity` is absent.
   - `date = resource.effectiveDateTime`.
5. Verify `value` is a number (or can be cast to float). If not, treat as missing and return `-1`.
6. Return the extracted data in the format required by the task, e.g. `FINISH([value, date])` or embed in a sentence as instructed.

**Pattern 2: Age‑based ordering fallback**
1. After extracting `date`, compute the difference between the current task time (provided in the context) and `date`.
2. If the difference > 365 days, proceed to create a `ServiceRequest` for the appropriate LOINC code.
3. If the difference ≤ 365 days, do **not** order and simply return the value/date.

**Pattern 3: Formatting the final answer**
- For plain numeric answers: `FINISH([value])`.
- For value + date answers: `FINISH([value, date])`.
- Never wrap the numeric value with explanatory text; the task will add wording if needed.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6488980 and when was it recorded? If the result is older than 1 year, order a new HbA1C test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6488980`
2. Receive Bundle. Suppose `total = 1` and the entry contains:
   ```json
   {
     "resource": {
       "effectiveDateTime": "2022-09-01T08:30:00Z",
       "valueQuantity": {"value": 7.2, "unit": "%"}
     }
   }
   ```
3. Extract `value = 7.2`, `date = "2022-09-01T08:30:00Z"`.
4. Compute age: > 1 year → create ServiceRequest with LOINC `4548-4`.
5. POST the ServiceRequest.
6. Return `FINISH([7.2, "2022-09-01T08:30:00Z"])`.

**CORRECT output:** `FINISH([7.2, "2022-09-01T08:30:00Z"])`
**WRONG output:** `FINISH(["-1"])` when a valid observation exists.

## Success Indicators
- The agent inspects `bundle.total` and only returns `-1` when it is truly zero.
- The numeric value is returned without its unit, and the date is included when required.
- When the observation is older than the threshold, a correctly formed `ServiceRequest` is posted before finishing.

## Failure Indicators
- `FINISH(["-1"])` appears even though the bundle contained a valid Observation.
- The returned value includes the unit string (e.g., `"7.2%"`).
- The agent posts a ServiceRequest without first checking the observation age.
- The date field is omitted or malformed in the final answer.
