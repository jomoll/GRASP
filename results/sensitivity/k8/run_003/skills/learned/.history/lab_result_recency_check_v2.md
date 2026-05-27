---
description: "Validate extracted lab values and use -1 only when no recent result\
  \ with a parsable numeric value exists. Added tolerant extraction and unit\u2011\
  handling to avoid false\u2011negative -1 responses."
name: lab_result_recency_check
provenance:
  action: MODIFY
  epoch: 1
  fixes: 10
  parent_version: 1
  probe_score: 6
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task10_17
  - task4_28
  - task9_28
  - task9_22
  - task5_17
  - task10_20
  - task10_27
  - task5_3
  - task9_11
  update_cycle: 0
tags: []
version: 2
---

# Lab Result Recency and Value Validation (Revised)

## Pattern Description
This skill checks that a recent Observation exists **and** that a **parsable numeric value** can be obtained from it. If a recent Observation is found but its value cannot be parsed (e.g., missing `valueQuantity`, malformed `valueString`, or unexpected component layout), the task is treated as *no valid result* and the sentinel `-1` is returned. The logic is deliberately tolerant: any numeric value found – regardless of unit presence – is accepted; unit conversion is applied only when the unit is known and a conversion factor is defined.

## When to Use This Skill
- Tasks that request the most recent numeric value of a lab Observation (e.g., magnesium, potassium, HbA1c) within a defined time window.
- The answer format requires a single number (or `-1` as a sentinel).
- Observations may store the value in `valueQuantity`, `valueString`, or as a component of a composite Observation.

## Revised Extraction & Recency Procedure
1. **GET** the Observation bundle: `GET /Observation?code={CODE}&patient={MRN}`.
2. **Collect** all entries in `bundle.entry` that contain an `resource` of type `Observation`.
3. **Filter by recency**:
   - Keep only entries whose `effectiveDateTime` is **≥** (`referenceTime` – `window`).
   - If an entry lacks `effectiveDateTime`, exclude it (it cannot be proven recent).
4. **Sort** the remaining entries by `effectiveDateTime` descending and **select the first** (most recent).
5. **Extract a numeric value** from the selected Observation using the following tolerant cascade:
   - **a.** If `valueQuantity.value` exists and is a number → use it.
   - **b.** Else if `valueQuantity.value` is missing but `valueString` exists → parse the first numeric token from the string (ignore surrounding text/units).
   - **c.** Else if the Observation contains a `component` array, locate a component whose `code.coding.code` matches the requested LOINC (or the same code used in the query) and extract its `valueQuantity.value` (or parse its `valueString` similarly).
   - **d.** If none of the above yield a number, treat the Observation as **invalid** and continue to step 7.
6. **Unit handling (optional):**
   - If the extracted value has an associated `unit` and the task specifies a required unit, apply a known conversion factor (e.g., `mmol/L → mg/dL` using 2.08). 
   - If the unit is unknown or conversion is not defined, **return the raw numeric value** (do not reject it).
7. **Placeholder fallback:**
   - If **no Observation** meets the recency window **or** the most recent Observation does not yield a parsable numeric value, return the sentinel `-1`.

## Formatting Rule
- The final `FINISH` call must be exactly: `FINISH([value])` where `value` is the numeric result (after any conversion) or `-1`.
- No extra text, units, or additional array elements are allowed.

## Success Indicators
- `FINISH` contains a single numeric element (or `-1`).
- The numeric value matches the most recent Observation’s parsable number, with conversion applied only when defined.
- No explanatory text or units appear in the `FINISH` payload.

## Failure Indicators
- `FINISH` returns `-1` while a recent Observation with a parsable numeric value exists.
- The payload includes strings, extra array elements, or units.
- An older Observation is selected because sorting was omitted.
- The agent returns `null` or an empty array instead of `-1` when no result is available.

## Guard Clause for Regression Cases
- This revision **does not require** the presence of a specific unit; it will accept a numeric value even if the unit is missing or unexpected. This prevents false‑negative `-1` responses in cases where the Observation stores a valid number but lacks the exact expected unit (e.g., magnesium recorded as `2.2` with no unit).
