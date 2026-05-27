---
description: "Improve medication name extraction to resolve references and normalize\
  \ for OR\u2011logic queries."
name: medication_name_extraction
provenance:
  baseline_fixes: 2
  baseline_regressions: 3
  epoch: 11
  failure_mode: or_logic_aggregation_error
  fixes: 4
  parent_version: 1
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 00c6c1102d545178bf7380f3
  - 047259e83745142834b50838
  update_cycle: 0
tags: []
version: 2
---

## When to use
You must activate this skill whenever a question involves checking the presence or details of specific medications from `MedicationRequest` resources, especially when the query contains OR‑logic (e.g., *"clonidine patch 0.2 mg/24 hr, atorvastatin, or prasugrel"*).

## Procedure
1. **Ensure a FHIR query** – If the current context does not already contain `Medication` resources referenced by any `MedicationRequest`, call `get_resources_by_resource_id` for each unique `Medication/<id>` found in `medicationReference` fields.
2. **Build a lookup table** – Create a dictionary `med_by_id` mapping medication IDs to their full `Medication` resource.
3. **Extract name from each MedicationRequest**:
   - If `medicationCodeableConcept` is present, use the first `coding.display` (fallback to `coding.code`).
   - Else if `medicationReference` exists, look up the referenced Medication in `med_by_id` and extract:
     * `code.coding[0].display` or `code.coding[0].code`
     * if missing, `product.form.text`
     * if still missing, the first `product.ingredient.itemCodeableConcept.coding[0].display`
   - If none of the above yield a name, return `None` for this request.
4. **Normalize the extracted name** – Strip whitespace, collapse internal spaces, and convert to lower‑case.
5. **Match against target list** – For OR‑logic questions, compare the normalized name to each normalized target using exact equality; also allow a target to match if it is a substring of the name when the target is a generic term like "soln".
6. **Aggregate results** – Produce a dictionary `{target: "Yes" if found else "No"}` for all targets.

## Checks
- Verify that at least one `MedicationRequest` resource is present.
- Confirm that any `medicationReference` IDs have been fetched; if not, raise a warning and skip that request.
- Ensure the final answer type matches the question’s expected structure (e.g., a dict of Yes/No per medication).
- Validate that all target strings have been normalized in the same way before comparison.

## Avoid
- Assuming a medication name can be taken from the `MedicationRequest` without checking the referenced `Medication` resource.
- Returning a single Yes/No for the whole OR list; each medication must be evaluated separately.
- Matching on partial strings without explicit substring logic for generic terms (e.g., "soln").
- Leaving timezone information in normalized names (names should be plain text, not dates).
