---
description: Resolves medicationReference IDs to Medication resources before substring
  matching.
name: medication_name_substring_match_enforcer
provenance:
  baseline_fixes: 8
  baseline_regressions: 5
  epoch: 8
  failure_mode: medication_reference_not_resolved_in_prescription_query
  fixes: 6
  parent_version: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 047259e83745142834b50838
  update_cycle: 0
tags: []
version: 2
---

## When to use
Trigger this skill whenever a question requires matching medication names in `MedicationRequest` resources and the request may use a `medicationReference` instead of (or in addition to) a `medicationCodeableConcept`.
Typical patterns include boolean checks like *"Did the patient receive clonidine patch?"* or counting distinct drugs where the medication is referenced by ID.

## Procedure
1. **Ensure Medication data is available** – rely on `resource_query_precheck_medicationrequest` to have fetched all `Medication` resources for the patient.
2. **Build a lookup table**:
   - Iterate over the retrieved `Medication` resources.
   - For each resource, collect all possible name strings:
     - `code.coding[].display`
     - `code.coding[].code`
     - `code.text`
   - Normalise each string by collapsing whitespace and lower‑casing it.
   - Store the set of normalised names keyed by the Medication resource `id`.
3. **Process each MedicationRequest**:
   - If the request has a `medicationReference`, extract the referenced Medication ID (`reference.split('/')[-1]`).
   - Retrieve the pre‑computed name set from the lookup table and add those names to the candidate list.
   - If the request also contains a `medicationCodeableConcept`, extract its display/text strings in the same way and add them to the candidate list.
4. **Normalise candidate names** (collapse whitespace, lower‑case).
5. **Perform substring matching**:
   - Normalise the target medication strings from the question in the same way.
   - Consider a match if the target is a substring of a candidate *or* the candidate is a substring of the target.
6. **Aggregate the result** according to the question type (boolean existence, count of distinct drugs, etc.).

## Checks
- Verify that at least one `Medication` resource was retrieved; if none, fall back to matching only `medicationCodeableConcept` values.
- Confirm that each `MedicationReference` resolves to a known Medication ID; if the ID is missing, ignore that request but do not error.
- Ensure all string normalisation steps are applied consistently to both targets and candidates.
- Validate the final answer type matches the question (e.g., boolean, integer, list) before returning.

## Avoid
- Skipping the lookup of `medicationReference` IDs – this was the root cause of missed matches.
- Matching only exact strings; always use case‑insensitive substring matching after normalisation.
- Forgetting to include `code.coding[].code` or `code.text` from the Medication resource, which may hold the drug name.
- Returning a non‑boolean answer for a yes/no question; enforce the correct type after aggregation.
