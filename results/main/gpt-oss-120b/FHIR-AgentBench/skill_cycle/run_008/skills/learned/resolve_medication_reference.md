---
description: Fetch Medication resources referenced by MedicationRequest to obtain
  drug names and details for queries.
name: resolve_medication_reference
provenance:
  baseline_fixes: 4
  baseline_regressions: 1
  epoch: 5
  failure_mode: medication_reference_not_resolved
  fixes: 6
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 07bde541ff2932869ecb4912
  - 081ba7feccd490013f102984
  - 08e4e46ffbf10a71b11cc538
  update_cycle: 1
tags: []
version: 1
---

## When to use
You should invoke this skill whenever a question involves medication names, routes, doses, or counts and the patient’s `MedicationRequest` resources contain a `medicationReference` (i.e., the medication is stored as a separate `Medication` resource rather than inline `medicationCodeableConcept`). Typical triggers are:
- "Has patient X been prescribed docusate sodium?"
- "Total dose of omeprazole prescribed during the last hospital encounter"
- "Count distinct drugs prescribed in April"
- Any query that needs the display/name of a medication but the `MedicationRequest` only has a reference.

## Procedure
1. **Identify needed MedicationRequests**
   - After you have issued `get_resources_by_patient_fhir_id` for `MedicationRequest`, filter them according to the question (date range, encounter reference, route, etc.).
2. **Collect unique Medication IDs**
   - For each retained `MedicationRequest`, if `medicationReference` exists, extract the ID from the reference string (it will be of the form `Medication/<id>`). Add the ID to a set.
3. **Fetch Medication resources**
   - For every ID in the set, call `get_resources_by_resource_id` with `resource_type="Medication"` and `resource_id=<id>`.
   - Store the returned resources in a dictionary `med_id -> resource`.
4. **Build a display map**
   - For each fetched Medication, obtain a human‑readable name:
     - Prefer `code.coding[*].display` (first non‑empty).
     - If no display, fall back to `code.coding[*].code`.
     - If still missing, use `code.text`.
   - Store `med_id -> name`.
5. **Enrich MedicationRequests**
   - When processing a `MedicationRequest`:
     - If `medicationCodeableConcept` is present, use its display as usual.
     - Otherwise, look up the name from the display map using the `medicationReference` ID.
6. **Perform the original query logic**
   - Now that every request has a resolved name, apply the intended aggregation (e.g., existence check, sum of `dose_val_rx`, count of distinct names, etc.).
7. **Return answer**
   - Format the answer exactly as the question expects (plain "Yes/No", numeric total, list of drug names, etc.).

## Checks
- Verify that for every `MedicationRequest` you used, a corresponding `Medication` resource was fetched if it relied on `medicationReference`.
- Confirm that the display map contains a non‑empty string for each ID; if a name cannot be resolved, log a warning and skip that request.
- Ensure dose fields (`dose_val_rx`, `dosageInstruction.doseQuantity.value`, etc.) are parsed as floats before aggregation.
- Validate that the final answer matches the required type (boolean, number, string list) and units (e.g., mg, ml) if the question specifies them.

## Avoid
- Assuming a `MedicationRequest` always has an inline `medicationCodeableConcept`.
- Ignoring `medicationReference` and therefore returning empty or incorrect drug names.
- Fetching the same Medication resource multiple times; deduplicate IDs before calling the API.
- Including Medication resources that are unrelated to the filtered MedicationRequests.
- Returning dosage totals when the dose field is missing or not numeric.
