---
description: Extract numeric values and timestamps from Observation resources, handling
  missing fields and diverse formats.
name: observation_value_extraction
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 1
  failure_mode: exception_during_answer_generation
  fixes: 4
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 0114a64085ec7d751f6e1bfd
  - 01389011a3cea028b226b95b
  - 09469e7ae520d7c2a28ad15f
  - 0a36ca6e9f221dc69fc7f8de
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should invoke this skill whenever a question requires you to read a numeric laboratory or vital‑sign value from an Observation (e.g., respiratory rate, creatinine, chloride, weight) and you need the associated timestamp. Typical triggers are patterns like "change of X between <time> and <time>", "first/last measurement", "maximum value since …", or any comparison of two Observation values.

## Procedure
1. **Retrieve Observations** – Use `get_resources_by_patient_fhir_id` with `resource_type="Observation"` for the target patient.
2. **Identify relevant observations** – For each Observation `o`:
   - Build a normalized search string from `o['code']['coding'][*]['display']`, `o['code']['coding'][*]['code']`, and `o['code'].get('text','')` (lower‑case, stripped).
   - If the search string contains the target concept (e.g., "respiratory rate", "chloride", "daily weight"), keep the observation.
3. **Parse the effective datetime** – Prefer `o.get('effectiveDateTime')`; if missing, fall back to `o.get('effectivePeriod',{}).get('start')`. Convert the string to a `datetime` object:
   - Replace a trailing `Z` with `+00:00` before parsing.
   - Use `datetime.fromisoformat` and strip any timezone information (`replace(tzinfo=None)`).
   - If parsing fails, skip the observation.
4. **Extract the numeric value** – Attempt, in order:
   - `o.get('valueQuantity',{}).get('value')`
   - `o.get('valueInteger')`
   - `float(o.get('valueString'))` (catch `ValueError`).
   - If none are present or conversion fails, treat the value as missing and skip the observation.
5. **Collect results** – Append a tuple `(dt, value)` to a list `results` for each successfully parsed observation.
6. **Sort** – After processing all observations, sort `results` by the datetime component.
7. **Return** – Provide the sorted list of `(datetime, value)` tuples to the calling skill or answer generator.

## Checks
- Verify that each returned tuple contains a valid `datetime` (no `None`).
- Ensure the numeric value is a real number (`int` or `float`).
- Confirm that at least one observation was found; if the list is empty, the higher‑level skill should respond with "No data found" or a similar graceful message rather than raising an exception.
- All timestamps must be timezone‑agnostic (converted to naive UTC) to allow correct ordering and comparison.

## Avoid
- Assuming a specific field (`valueQuantity`) always exists; many observations store the value in `valueInteger` or `valueString`.
- Raising an exception when a timestamp or value is missing; instead, simply skip that observation.
- Performing case‑sensitive string matches on code displays; always normalise to lower case and strip whitespace.
- Returning unsorted results, which can cause later comparison logic to fail.
