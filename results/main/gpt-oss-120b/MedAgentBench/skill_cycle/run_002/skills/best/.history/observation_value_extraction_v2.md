---
description: Extract numeric lab value and timestamp from Observation bundles, returning
  -1 only when no valid result exists
name: observation_value_extraction
provenance:
  action: MODIFY
  epoch: 2
  fixes: 6
  parent_version: 1
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task8_13
  - task5_16
  - task9_11
  - task9_14
  - task5_7
  - task9_3
  update_cycle: 0
tags: []
version: 2
---

# Observation Value Extraction

## Pattern Description
You must reliably pull a single numeric result and its recording time from any FHIR Observation search bundle. The skill works for any lab code (e.g., HbA1c, magnesium, potassium) and must return the most recent *valueQuantity.value* together with the *effectiveDateTime* (or *issued* if the former is missing). If the bundle contains no entries, or none of the entries have a usable numeric value, you return `[-1]` (or `[-1, ""]` for paired value/date tasks). This pattern replaces the previous placeholder‑only behavior that caused many tasks to answer `-1` even when a valid result was present.

## When to Use This Skill
- After a `GET /Observation?code={code}&patient={MRN}` that returns a `Bundle` with `type="searchset"`.
- The task asks for the *most recent* lab value (e.g., "last HbA1c", "most recent magnesium level within 24 h").
- The required output is a numeric value, optionally paired with a timestamp.
- The bundle may contain multiple `entry` objects, pagination links, or nested resources.

## Common Failure Patterns
- Returning `[-1]` simply because `total` > 0 but the agent never inspected `entry[0].resource`.
- Looking only at the first entry regardless of date, causing stale values to be returned.
- Extracting `valueString` or concatenating the unit (e.g., `"5.4%"`) instead of the raw number.
- Ignoring `effectiveDateTime` and using `issued` or `meta.lastUpdated` incorrectly.
- Failing to convert units when the Observation uses a different unit than the task expects (e.g., mmol/L → mg/dL).

## Recommended Patterns
**Pattern 1: Core extraction strategy**
1. Verify the response is a `Bundle` with `type="searchset"`.
2. If `total == 0`, return `[-1]` (or `[-1, ""]`).
3. Iterate over `entry` objects and collect those whose `resource.resourceType == "Observation"` and that contain a numeric `valueQuantity.value`.
4. For each candidate, record:
   - `value = entry.resource.valueQuantity.value` (as a number, **do not** include the unit string).
   - `date = entry.resource.effectiveDateTime` if present, otherwise `entry.resource.issued`.
5. Sort candidates by `date` descending and pick the first (most recent).
6. Return `[value, date]` (or just `[value]` if the task expects a single number).

**Pattern 2: Fallback when `valueQuantity` missing**
- If no `valueQuantity` is found, look for `valueString` that can be parsed as a number (strip non‑numeric characters).
- If still none, treat as no valid result and return `[-1]`.

**Pattern 3: Unit handling**
- If the task specifies a target unit (e.g., mg/dL for magnesium) and the Observation’s `valueQuantity.unit` differs, apply the appropriate conversion before returning the value.
- Example conversion: `mmol/L → mg/dL` for magnesium multiply by 1.95.

## Example Application
**Task:** "What’s the last HbA1c value for patient S0722219 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S0722219`
2. Response bundle contains three entries; each entry.resource has `valueQuantity.value` and `effectiveDateTime`.
3. Extract the three `(value, date)` pairs, e.g., `(6.5, "2022-03-08T08:14:00+00:00")`, `(6.2, "2023-06-01T09:00:00+00:00")`, `(5.9, "2023-11-01T10:00:00+00:00")`.
4. Sort by date → most recent is `(5.9, "2023-11-01T10:00:00+00:00")`.
5. Return `FINISH([5.9, "2023-11-01T10:00:00+00:00"])`.

**CORRECT:** `valueQuantity.value` extracted as a number, date taken from `effectiveDateTime`.
**WRONG:** `FINISH([-1])` because the agent never inspected `entry` objects.

## Success Indicators
- The agent returns a numeric value (or `-1` only when the bundle truly has no usable Observation).
- The returned timestamp matches the `effectiveDateTime` of the most recent Observation.
- No unit strings are concatenated to the numeric value.
- For tasks with a 24‑hour filter, the returned date is within the required window.

## Failure Indicators
- `FINISH([-1])` despite `total > 0` and visible numeric values in the bundle.
- Returned value includes non‑numeric characters (e.g., `"5.4%"`).
- Timestamp is missing, empty, or taken from the bundle’s `meta.lastUpdated` instead of the Observation’s own date.
- The most recent value is not selected (older value returned).
