---
description: Enhance to resolve medicationReference links in MedicationRequest/MedicationAdministration.
name: resource_query_planner
provenance:
  baseline_fixes: 3
  baseline_regressions: 4
  epoch: 3
  failure_mode: medication_reference_not_resolved
  fixes: 5
  parent_version: 1
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 00beff4406c2ee10ac9621fe
  - 0406ba9fa1c3ada7f76965a3
  - 047259e83745142834b50838
  - 081ba7feccd490013f102984
  - 08e4e46ffbf10a71b11cc538
  update_cycle: 0
tags: []
version: 2
---

## When to use
You must invoke this skill whenever a question requires medication names, codes, or dose information and the patient’s **MedicationRequest** (or **MedicationAdministration**) resources may contain a **medicationReference** instead of an inline **medicationCodeableConcept**. This includes queries about specific drugs, dose totals, or last‑prescribed medication where the reference must be resolved.

## Procedure
1. **Fetch primary medication resources** – Retrieve all **MedicationRequest** (and optionally **MedicationAdministration**) for the target patient using `get_resources_by_patient_fhir_id`.
2. **Collect referenced Medication IDs** – Iterate over the fetched resources and extract any `medicationReference.reference` values that start with `Medication/`. Store the unique IDs in a set.
3. **Bulk‑fetch Medication resources** – For each unique Medication ID, call `get_resources_by_resource_id` (or batch‑fetch if supported) to obtain the full **Medication** resource.
4. **Build a lookup table** – From each Medication resource, derive a human‑readable name:
   - Prefer `code.coding.display`.
   - Fallback to `code.coding.code`.
   - Finally use `code.text` if present.
   Store the mapping `{med_id: name.lower().strip()}` in a temporary variable (e.g., `med_id_to_name`).
5. **Expose the mapping** – Make `med_id_to_name` available to downstream skills (e.g., `observation_value_extraction` or custom medication extraction logic) so they can substitute the reference with the resolved name when matching drug terms or extracting dose fields.
6. **Handle missing references** – If a MedicationReference cannot be resolved (no resource returned or name missing), log a warning and continue; downstream skills should treat the entry as “unknown” rather than silently dropping it.

## Checks
- Verify that every `medicationReference` extracted in step 2 has a corresponding entry in the lookup table after step 4.
- Confirm that each fetched resource is of type **Medication** and contains at least one coding/display element.
- Ensure the lookup table keys are the raw IDs (without the `Medication/` prefix) and values are non‑empty strings.
- Before proceeding to answer generation, assert that the patient’s medication list (including resolved references) is complete for the time window required by the question.

## Avoid
- Skipping step 2 and relying only on `medicationCodeableConcept`; this was the root cause of the "medication_reference_not_resolved" failures.
- Over‑fetching unrelated resources – only request Medication IDs that actually appear in the patient’s MedicationRequest/MedicationAdministration.
- Assuming a single naming field; always apply the fallback order to avoid empty names.
- Returning duplicate entries – the set in step 2 guarantees uniqueness.
