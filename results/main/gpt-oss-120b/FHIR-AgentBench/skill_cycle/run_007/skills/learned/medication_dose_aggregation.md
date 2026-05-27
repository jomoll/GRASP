---
description: Aggregate prescribed dose for a specific medication across relevant MedicationRequest
  resources, but only activate when the user question clearly asks for a total medication
  dose.
name: medication_dose_aggregation
provenance:
  baseline_fixes: 2
  baseline_regressions: 1
  epoch: 10
  failure_mode: unlabeled
  fixes: 4
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - 081ba7feccd490013f102984
  - 0874a8eb9ae4f8b6bb50a1d4
  - 09469e7ae520d7c2a28ad15f
  update_cycle: 1
tags: []
version: 1
---

## When to use
When a question explicitly asks for the **total amount** of a particular medication prescribed during a defined encounter, visit, or time period (e.g., “total ondansetron dose prescribed on the last hospital visit”). The question must contain medication‑related keywords such as *dose*, *total*, *prescribed*, *MedicationRequest*, or a specific medication name.

## Guard clause (trigger detection)
1. **Inspect the user query**. If the query does **not** contain any of the following (case‑insensitive) substrings, skip this skill and let other skills handle the request:
   - "dose"
   - "total"
   - "prescribed"
   - "medicationrequest"
   - a known medication name (detected via the existing `medication_name_extraction` helper)
2. If the guard clause fails, return `None` (no answer) so the orchestrator can try alternative skills.

## Procedure (executed only after the guard passes)
1. **Determine scope** – Identify the encounter(s) or date range referenced in the question (e.g., "last hospital visit", "ICU stay on 2023‑05‑12").
2. **Fetch MedicationRequests** – Call `get_resources_by_patient_fhir_id(patient_id, "MedicationRequest")` to retrieve all MedicationRequest resources for the patient.
3. **Filter by encounter** –
   - If the question mentions a specific encounter ID, keep only those MedicationRequests whose `encounter.reference` ends with that ID.
   - If no explicit reference is present, retain requests whose `effectivePeriod` (or `authoredOn` when period is missing) falls within the identified encounter dates.
4. **Select medication** – Use the existing `medication_name_extraction` logic to obtain a normalized medication name for each request (display → code → referenced Medication → product/form text). Compare it case‑insensitively and whitespace‑agnostically with the medication name extracted from the question.
5. **Extract dose value** – For each matching request:
   - Prefer `dosageInstruction[*].doseAndRate[*].doseQuantity.value`.
   - Fallback to `dosageInstruction[*].doseQuantity.value`.
   - If still missing, look for an extension whose `url` ends with `dose_val_rx` and read its `valueString` or `valueQuantity`.
   - Convert the extracted value to `float`. If conversion fails, log the omission and continue.
6. **Aggregate** – Sum all numeric dose values. Track units:
   - If every extracted dose shares the same unit (e.g., mg), keep that unit.
   - If multiple units appear, note the ambiguity and return the raw sum without a unit.
7. **Produce answer** – Return only the numeric total (as an integer when the sum is whole) and, when a single clear unit exists, append it separated by a space (e.g., `120 mg`). No additional explanatory text.

## Checks
- Ensure at least one MedicationRequest remains after filtering; otherwise return a clear “no data” response.
- Verify that the medication name comparison is case‑insensitive and whitespace‑agnostic.
- Confirm each extracted dose is numeric; skip non‑numeric entries but record that they were ignored.
- If unit ambiguity occurs, return the sum alone and optionally add a short note like `"unit ambiguous"` **only** if the downstream `answer_format_validation` permits free‑form text; otherwise omit the note.
- Pass the final string through `answer_format_validation` before returning.

## Avoid
- Summing doses from unrelated encounters or outside the requested time window.
- Using `dispenseRequest.quantity` when the question asks for the prescribed dose.
- Double‑counting the same MedicationRequest.
- Assuming a unit when none is present; return only the numeric total in that case.
- Emitting extra prose; output must be strictly the number and optional unit.
