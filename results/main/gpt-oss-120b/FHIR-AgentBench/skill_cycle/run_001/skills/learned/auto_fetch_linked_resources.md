---
description: "Retrieve MedicationRequest or Observation resources linked to a patient\u2019\
  s encounter and apply optional code, route, date\u2011range or dose\u2011aggregation\
  \ filters."
name: auto_fetch_linked_resources
provenance:
  baseline_fixes: 6
  baseline_regressions: 4
  epoch: 4
  failure_mode: no_resource_query_performed
  fixes: 9
  probe_score: 6
  regressions: 1
  triggering_sample_ids:
  - 06b1eef22357320dc0f8a64a
  - 0741b96a36302acf8ace5c02
  - 07f02f8bb9cf48ec09ba120e
  - 081ba7feccd490013f102984
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must invoke this skill whenever a question refers to a medication, laboratory test, or observation **tied to a specific encounter** (e.g., *first hospital encounter*, *last hospital visit*, *ICU stay*) and the query includes any of:
- a medication route (IV, IH, PO, etc.)
- a lab/observation code or free‑text keyword (sodium, microbiology, hematocrit, etc.)
- a date range or “since …” clause
- a request to sum or compare doses (e.g., total ondansetron dose)
If the agent has not yet performed a `get_resources_by_patient_fhir_id` call for the needed resource type, this skill should be triggered.

## Procedure
1. **Identify the target encounter**
   - Call `get_resources_by_patient_fhir_id` with `resource_type="Encounter"`.
   - From the returned encounters, select the one that matches the temporal qualifier in the question (first, last, specific month, etc.).
   - Use the same hospital‑encounter heuristics already employed in other skills (identifier system contains `encounter-hosp`, class.code = `IMP`/`INPATIENT`/`ACUTE` with type display containing “hospital”, etc.).
2. **Fetch the relevant resource type**
   - If the question mentions a medication, request `MedicationRequest` resources.
   - If it mentions a lab test, observation, or numeric value, request `Observation` resources.
3. **Filter by encounter reference**
   - Keep only resources whose `encounter.reference` ends with the selected encounter’s `id` (or that belong to child encounters whose `partOf.reference` points to the selected encounter).
4. **Apply additional filters**
   - **Route filter** (for MedicationRequest): inspect each `dosageInstruction[*].route.coding.display` or `route.text` for the target route string (case‑insensitive, whitespace‑agnostic).
   - **Code/keyword filter** (for Observation): search `code.coding.display`, `code.coding.code`, and `code.text` for the supplied keyword(s) using a case‑insensitive regex.
   - **Date‑range filter**: parse `effectiveDateTime` or `effectivePeriod.start` and keep only those within the requested window.
5. **Optional dose aggregation** (MedicationRequest only)
   - For each retained medication request, locate `dosageInstruction[*].doseAndRate[*].doseQuantity.value` and its `unit`.
   - Convert all values to a common unit if multiple units appear (use the first unit as reference; if conversion is impossible, abort with a clear error).
   - Sum the numeric values to produce the total dose.
6. **Return the filtered set**
   - For simple existence queries, return a Boolean indicating whether any resource survived the filters.
   - For value‑retrieval queries, return the latest (or earliest, max, min, as requested) resource’s value and unit.
   - For aggregation queries, return the computed total dose and its unit.

## Checks
- Verify that at least one `Encounter` was found; otherwise answer “No matching encounter found”.
- Ensure the filtered resource list is non‑empty before extracting values; if empty, answer according to the question (e.g., `false`, `None`, or a descriptive message).
- Confirm that all datetime values are parsed without timezone offsets; compare them after normalising to naive UTC.
- When aggregating doses, confirm all units are identical (or convertible) and that every dosage entry contains a numeric `value` field.
- The final answer must match the expected format: Boolean, ISO‑8601 datetime string, numeric value with unit (e.g., `45 kg`), or numeric total dose with unit.

## Avoid
- Assuming a medication belongs to an encounter just because the patient ID matches; always check the explicit `encounter` reference.
- Matching route or code substrings without normalising whitespace and case (e.g., “iv drip” vs “IV‑DRIP”).
- Summing doses that use different units without conversion.
- Returning raw resource objects; always extract and format the specific answer element required by the question.
- Treating a missing `effectiveDateTime` as a valid timestamp; discard such observations.
