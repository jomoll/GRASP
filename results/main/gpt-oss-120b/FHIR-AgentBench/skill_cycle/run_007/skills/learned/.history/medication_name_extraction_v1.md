---
description: Extract the correct medication name from MedicationRequest, preferring
  display text and resolving references.
name: medication_name_extraction
provenance:
  baseline_fixes: 2
  baseline_regressions: 3
  epoch: 6
  failure_mode: medication_name_wrong_field_extracted
  fixes: 3
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - 01bc93ed00df686c5593006f
  - 0406ba9fa1c3ada7f76965a3
  - 09315d12007c47ae3fb400b6
  update_cycle: 1
tags:
- medication
- extraction
- reference_resolution
version: 1
---

## When to use
You should invoke this skill whenever a question asks for the *name* of a medication prescribed to a patient (e.g., "What medication was prescribed...", "last medication", "drug name", etc.). It covers both direct `medicationCodeableConcept` fields and indirect `medicationReference` fields that point to a `Medication` resource.

## Procedure
1. **Ensure a MedicationRequest query has been executed** (the `ensure_fhir_query_executed` skill will have run).
2. **Filter the retrieved MedicationRequest resources** according to any temporal, route, or other criteria expressed in the question.
3. **For each candidate MedicationRequest, obtain the medication name using the following priority order:**
   - a. If `medicationCodeableConcept.coding[0].display` exists, use it.
   - b. Else if `medicationCodeableConcept.coding[0].code` exists, use it.
   - c. Else if `medicationReference.reference` is present, extract the referenced Medication ID, fetch the corresponding `Medication` resource, and:
      - i. Use `Medication.code.coding[0].display` if available.
      - ii. Otherwise use `Medication.code.coding[0].code`.
      - iii. If still missing, fall back to `Medication.product.form.text` or `Medication.product.ingredient[0].itemCodeableConcept.coding[0].display`.
4. **Trim whitespace and normalize case** (strip surrounding spaces, keep original casing for display).
5. **If multiple candidates remain after filtering, apply the ordering requested by the question** (e.g., last, first, maximum, minimum) using the appropriate date field (`authoredOn`, `occurrenceDateTime`, etc.).
6. **Return the selected medication name** as a plain string.

## Checks
- Verify that the final answer is a non‑empty string and does **not** look like a UUID or resource reference (e.g., does not match the pattern `[A-Za-z0-9-]{36}` or contain a slash).
- Confirm that the answer comes from the fields listed in the priority order above.
- Ensure any date‑based ordering respects the time window specified in the question.
- If no medication name can be resolved, answer `None` or a clear “No medication found” message.

## Avoid
- Returning the raw Medication reference ID (`Medication/<id>`) or the MedicationRequest ID.
- Using the `Medication.id` field as the medication name.
- Ignoring the need to resolve `medicationReference` to the actual Medication resource.
- Selecting a name from unrelated fields such as `note.text` or `dosageInstruction`.
