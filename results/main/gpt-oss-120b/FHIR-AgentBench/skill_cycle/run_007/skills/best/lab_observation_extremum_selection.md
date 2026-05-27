---
description: Select first/last or max/min lab Observation values within a specific
  encounter and time window.
name: lab_observation_extremum_selection
provenance:
  baseline_fixes: 1
  baseline_regressions: 2
  epoch: 12
  failure_mode: medication_reference_not_resolved
  fixes: 4
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 02a069698a803a8419fa294c
  - 03d470fc8e41f5dd8568f771
  - 05a9aa5bb494b962444ac354
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill for any question that asks for the **first**, **last**, **maximum**, **minimum**, or **extreme** value of a lab measurement (e.g., blood pressure, creatinine, amylase) during a particular encounter (first/last hospital visit, ICU stay, etc.) or within a defined date range.

## Procedure
1. **Identify the target encounter**
   - Use the existing `admission_type_field_selection` or encounter‑filter logic to obtain the relevant `Encounter` (first, last, or by identifier).
   - Record its `id` and, if needed, its `period.start` / `period.end` to bound observations.
2. **Fetch Observation resources** for the patient (already available from the query).
3. **Filter observations**
   - Keep only those whose `encounter.reference` ends with the target encounter `id` (or that fall inside the encounter period if no reference).
   - Keep only observations whose `code.coding` (or `code.text`) matches the lab test name supplied in the question (case‑insensitive, allow partial matches).
   - Apply any explicit date window (e.g., "since 03/2161") using `effectiveDateTime`, `issued`, or `effectivePeriod.start`.
4. **Extract numeric value**
   - Prefer `valueQuantity.value` (store unit from `valueQuantity.unit`).
   - If missing, try parsing `valueString` as a float.
   - Discard observations without a numeric value.
5. **Determine extremum**
   - If the query asks for **first** or **last**, sort by the observation datetime and pick the earliest or latest.
   - If it asks for **maximum** or **minimum**, compute the max/min of the numeric values; if multiple share the extreme value, choose the latest datetime among them.
6. **Format answer**
   - Return the datetime of the selected observation in ISO‑8601 (date‑only if the question asks for a date, otherwise full datetime).
   - If the unit is required (e.g., "mmHg"), append it after the numeric value when the question asks for the value itself.

## Checks
- Confirm the observation belongs to the chosen encounter (reference match or datetime within encounter period).
- Verify that at least one observation remains after filtering; otherwise return a clear "no data" response.
- Ensure the extracted value is a valid number before comparing for max/min.
- Validate the final datetime format matches the expected type (date vs datetime) inferred from the question.

## Avoid
- Selecting observations from unrelated encounters or outside the requested time window.
- Using the first coding entry blindly without checking for synonyms or partial matches.
- Returning the raw Observation resource instead of the requested datetime/value.
- Ignoring timezone offsets – always normalize to naive UTC before comparison.
