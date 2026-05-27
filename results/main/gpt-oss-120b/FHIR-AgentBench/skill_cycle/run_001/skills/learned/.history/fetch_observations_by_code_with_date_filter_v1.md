---
description: Retrieve Observation resources matching a lab/measurement code and optional
  date constraints.
name: fetch_observations_by_code_with_date_filter
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 2
  failure_mode: no_resource_query_performed
  fixes: 6
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - 0186746594c1cf90e38d4ffd
  - 02964db902a561eae10282a2
  - 065b726dbf86eb804accd168
  - 06b1eef22357320dc0f8a64a
  - 07f02f8bb9cf48ec09ba120e
  - 0a403bb61217529f94970734
  - 0ce9c8a93ef40fa209454a71
  - 0d0fa264d945b5ef90978c92
  - 0d3343e3e64231d00abab91e
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should invoke this skill when a question asks for a lab test, vital sign, or other observation value (e.g., basophils, sodium, blood pressure, base excess) for a specific patient, often with a time qualifier such as "since 2025‑03‑01", "in 04/this year", "last time", or "maximum/minimum value".

## Procedure
1. **Identify the target term** – extract the measurement name from the user query (e.g., "basophils", "systolic blood pressure", "base excess"). Normalize it (lower‑case, collapse whitespace).
2. **Determine date bounds** – parse any date information in the query:
   * "since <date>" → start = parsed date, end = now.
   * "in <MM>/this year" → start = first day of month in current year, end = last day of that month.
   * "last time" → start = beginning of patient record, end = now (later steps will pick the latest match).
   * If no explicit date, default to the entire record history.
3. **Query Observations** – call `get_resources_by_patient_fhir_id` with `resource_type="Observation"` and the patient’s FHIR ID.
4. **Filter by code** – for each Observation:
   * Examine `code.coding[*].display`, `code.coding[*].code`, and `code.text`.
   * Keep the observation if the normalized display or code contains the target term.
5. **Apply date filter** – for each retained observation, obtain the effective timestamp from `effectiveDateTime` or `effectivePeriod.start`. Keep it only if it falls within the start‑end window.
6. **Derive the answer** – based on the query intent:
   * **Existence** (e.g., "has the patient had a basophil test?"): return `True`/`False`.
   * **Last/first time**: select the observation with the latest/earliest timestamp and return its datetime ISO string.
   * **Maximum/Minimum value**: extract `valueQuantity.value` (or `value` if present), compute `max`/`min`, and return the numeric value with its unit (e.g., `"12.5 mg/dL"`).
   * **Count**: return the integer count of matching observations.
   * **Difference**: if the query asks for a change between two measurements, sort by timestamp, pick the required positions (first, second, last, second‑last) and compute the difference, appending the unit.
7. **Output** – format the answer exactly as the question expects (boolean, ISO datetime, numeric with unit, integer count, or numeric difference).

## Checks
* Verify that at least one Observation resource was retrieved; if none, answer appropriately (e.g., `No` or `None`).
* Ensure the effective timestamp can be parsed to a `datetime`; skip malformed entries.
* Confirm that a numeric `valueQuantity.value` exists when a value is required; otherwise, treat the observation as non‑matching.
* When returning a value, include its unit from `valueQuantity.unit` if available.
* Respect the requested time window and do not return observations outside it.

## Avoid
* Matching on unrelated codes that merely contain the target substring (use whole‑word or phrase matching after normalization).
* Ignoring the date constraint supplied in the query.
* Returning a list of observations when the question asks for a single value (e.g., last time, maximum).
* Forgetting to include the unit with numeric answers, which leads to answer‑format errors.
* Assuming the patient’s FHIR ID is always the same key; always use the ID provided in the conversation context.
