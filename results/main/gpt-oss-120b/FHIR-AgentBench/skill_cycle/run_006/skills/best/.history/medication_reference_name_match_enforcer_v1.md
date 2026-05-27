---
description: Resolve MedicationReference IDs before performing any medication name
  matching in queries
name: medication_reference_name_match_enforcer
provenance:
  baseline_fixes: 2
  baseline_regressions: 3
  epoch: 14
  failure_mode: medication_reference_not_resolved_before_query
  fixes: 2
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 00c6c1102d545178bf7380f3
  - 0266d6e5d007484e57bf12d6
  - 065b726dbf86eb804accd168
  - 0b9e619bdb576876f002d49a
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill whenever a question asks whether a patient was prescribed a specific drug (by name, substring, or pattern) and the answer depends on `MedicationRequest` resources.

## Procedure
1. **Pre‑check** – Ensure `MedicationRequest` resources for the patient have already been fetched (the `resource_query_precheck_medicationrequest` skill should have run).
2. **Gather referenced Medications**
   - Iterate over all retrieved `MedicationRequest` entries.
   - For each request, if `medicationReference.reference` starts with `Medication/`, extract the Medication ID.
   - Collect the set of unique Medication IDs.
3. **Fetch Medication resources**
   - Use `get_resources_by_resource_id` (or batch fetch) to retrieve the `Medication` resources for the IDs gathered in step 2.
4. **Build a name lookup table**
   - For each fetched `Medication`, create a list of possible name strings:
     * All `code.coding[].display`
     * All `code.coding[].code`
     * `code.text`
   - Store the mapping `{med_id: [name strings]}`.
5. **Derive medication names for each request**
   - For each `MedicationRequest`:
     * If it has a `medicationReference`, look up the name list from the table.
     * Otherwise, extract names directly from its `medicationCodeableConcept` using the same fields as above.
6. **Normalize strings**
   - Define `normalize(s) = lower(trim(collapse_whitespace(s)))`.
   - Apply `normalize` to both the target drug strings supplied by the question and every medication name obtained in step 5.
7. **Substring matching**
   - For each target, check if it appears as a substring of any normalized medication name.
   - Record a match if any target is found.
8. **Produce the answer**
   - If the original question expects a boolean, return `true`/`false`.
   - If it expects the drug name(s), return the matched name(s) (original case) or the Medication ID if the name could not be resolved.

## Checks
- Verify that at least one `Medication` resource was successfully retrieved for every referenced ID; if any lookup fails, fall back to the names available in `medicationCodeableConcept`.
- Confirm that the target list is non‑empty after normalization.
- Ensure the final answer respects the expected type (boolean, string, list) and includes units only when explicitly required.

## Avoid
- Using the raw reference ID (`Medication/<id>`) as the answer without resolving it to a human‑readable name.
- Skipping the lookup step when a `medicationReference` is present.
- Performing case‑sensitive or whitespace‑sensitive matches.
- Ignoring `medicationCodeableConcept` when no reference is available.
