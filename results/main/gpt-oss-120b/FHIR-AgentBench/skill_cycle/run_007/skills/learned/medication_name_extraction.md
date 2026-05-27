---
description: Resolve medicationReference IDs by fetching Medication resources before
  extracting names.
name: medication_name_extraction
provenance:
  baseline_fixes: 1
  baseline_regressions: 2
  epoch: 17
  failure_mode: no_answer_returned
  fixes: 2
  parent_version: 4
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - 00c6c1102d545178bf7380f3
  - 044289b85d5894aef9a9825d
  - 0702bc77d929f78085010bb0
  - 08e4e46ffbf10a71b11cc538
  - 09b1b086d491d385b6744dd6
  - 0d012e621517a4059d3caf10
  update_cycle: 0
tags: []
version: 5
---

## When to use
Trigger this skill whenever a question asks for medication names or presence of a drug and the `MedicationRequest` resources may contain a `medicationReference` instead of a direct `medicationCodeableConcept`.

## Procedure
1. **Identify MedicationRequests** relevant to the patient (already fetched by prior query).
2. **Collect all medicationReference IDs** from those requests (the part after `Medication/`).
3. **Issue a FHIR query** `get_resources_by_resource_id` for each collected ID with `resource_type="Medication"`.
4. **Cache the returned Medication resources** keyed by their `id`.
5. For each MedicationRequest, extract the medication name using:
   - If `medicationCodeableConcept` exists, take the first coding's `display` or `code` (fallback to `text`).
   - Else, look up the referenced Medication in the cache and extract name using the same priority (code.coding[0].display > code.coding[0].code > product.form.text > first ingredient display/code).
6. Return a list of resolved medication names (or a boolean answer if the question is yes/no).

## Checks
- Verify that at least one `MedicationRequest` was processed.
- Ensure every `medicationReference` has a corresponding fetched `Medication` resource; if any are missing, treat the name as unknown and continue.
- Confirm the extracted name is a non‑empty string before using it for matching or answering.

## Avoid
- Assuming the medication name is already present without fetching the referenced Medication resource.
- Ignoring `medicationReference` fields entirely, which leads to missed matches and no‑answer failures.
