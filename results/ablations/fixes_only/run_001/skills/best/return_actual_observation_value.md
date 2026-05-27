---
description: Extract the latest Observation value (and date) from a FHIR Bundle and
  return it instead of the placeholder "-1".
name: return_actual_observation_value
provenance:
  action: ADD
  epoch: 0
  fixes: 13
  probe_score: 12
  regressions: 0
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task4_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Return Actual Observation Value

## Pattern Description
You must turn a FHIR `Bundle` response from an `Observation` search into a concrete answer.  The central lesson is to locate the most recent `Observation` entry, read its quantitative value (or string value when appropriate), and format the result for the task.  If the bundle contains no matching entries, you return the sentinel `-1` (or a task‑specific “no result” message) **after confirming the absence**.  This pattern prevents the agent from echoing the placeholder without inspecting the payload.

## When to Use This Skill
- After a `GET /Observation?...` request that is expected to provide a lab or vital sign value.
- The task asks for the *last* value, a value *within a time window*, or a decision based on the value’s age.
- The response is a `Bundle` with `resourceType: "Bundle"` and `type: "searchset"`.

## Common Failure Patterns
- Returning `FINISH(["-1"])` without checking `total` or `entry` fields.
- Extracting the wrong field (e.g., using `effectiveDateTime` instead of `valueQuantity.value`).
- Ignoring the `valueQuantity.unit` and concatenating it to the number.
- Failing to sort observations by `effectiveDateTime` when multiple entries exist.

## Recommended Patterns
**Pattern 1: Locate the latest Observation**
1. Verify the bundle’s `total` field. If `total == 0` → go to *Pattern 3* (no result).
2. From `bundle.entry`, extract each `resource` (type `Observation`).
3. Sort the observations by `resource.effectiveDateTime` (ISO‑8601) descending.
4. Pick the first (most recent) observation.

**Pattern 2: Extract the numeric value**
- If `observation.valueQuantity` exists:
  - `value = observation.valueQuantity.value` (must be a number).
  - `unit = observation.valueQuantity.unit` (optional, keep for validation).
- Else if `observation.valueString` exists and the task expects a string (e.g., blood pressure), use that directly.
- Else if `observation.valueCodeableConcept` exists, use the displayed code.
- Record the observation date: `date = observation.effectiveDateTime`.

**Pattern 3: No matching Observation**
- Return the sentinel defined by the task. Most tasks in this corpus expect `FINISH(["-1"])` for “no recent result”.

**Pattern 4: Formatting the final answer**
- For numeric labs: `FINISH([value, "date"])` or `FINISH([value])` if only the value is required.
- For string vitals (e.g., BP): `FINISH(["valueString"])`.
- Never add explanatory text; the output must be a JSON array of raw values.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6550627 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6550627`
2. Receive bundle (example excerpt):
   ```json
   {
     "resourceType":"Bundle",
     "total":1,
     "entry":[{
       "resource":{
         "resourceType":"Observation",
         "valueQuantity":{"value":7.2,"unit":"%"},
         "effectiveDateTime":"2022-09-10T08:30:00+00:00"
       }
     }]
   }
   ```
3. `total` > 0 → sort (only one entry) → pick it.
4. Extract `value = 7.2`, `date = "2022-09-10T08:30:00+00:00"`.
5. Return `FINISH([7.2, "2022-09-10T08:30:00+00:00"])`.

**If the bundle had `total:0`** → return `FINISH(["-1"])`.

## Success Indicators
- The agent’s `FINISH` payload contains the numeric value (and date when required) instead of `"-1"` when the bundle includes observations.
- The extracted value matches `valueQuantity.value` from the most recent observation.
- No extra explanatory text appears in the output array.

## Failure Indicators
- `FINISH(["-1"])` is returned despite `total > 0`.
- The output includes units (e.g., `"7.2%"`) or explanatory sentences.
- The date returned is not the `effectiveDateTime` of the most recent observation.
- The agent crashes or returns an empty array.
