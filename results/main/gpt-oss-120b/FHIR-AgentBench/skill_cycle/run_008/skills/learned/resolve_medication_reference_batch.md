---
description: Fetch Medication resources for all medicationReference IDs and return
  a mapping of IDs to drug names
name: resolve_medication_reference_batch
provenance:
  baseline_fixes: 3
  baseline_regressions: 3
  epoch: 14
  failure_mode: medication_reference_not_resolved
  fixes: 3
  parent_version: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 03d470fc8e41f5dd8568f771
  - 0a8c46b684e72300d29c18aa
  - 0c6cdc444ee911941bfd23f0
  update_cycle: 0
tags: []
version: 2
---

## When to use
When a question requires the drug name(s) from `MedicationRequest` resources that only contain a `medicationReference` (no `medicationCodeableConcept`). Trigger this skill whenever you have a list of `MedicationRequest` resources and need to resolve their referenced `Medication` names for matching, counting, or reporting.

## Procedure
1. **Input** – Receive a list (or a single) `MedicationRequest` resources that have a `medicationReference` field.
2. **Extract IDs** – For each request, read `medicationReference.reference`. Strip any leading `Medication/` prefix and collect the raw IDs.
3. **Deduplicate** – Create a unique set of medication IDs to avoid duplicate fetches.
4. **Fetch Medication resources** – For every ID in the set, call the tool:
   ```json
   {"resource_type": "Medication", "resource_id": "<id>"}
   ```
   Store the returned resources.
5. **Extract drug name** from each fetched `Medication` resource using the following priority:
   - First `code.coding[*].display` (first non‑empty display).
   - If no display, then `code.coding[*].code`.
   - If still missing, use `code.text`.
   - If none are present, fall back to the raw ID string.
6. **Build mapping** – Create a dictionary `{ "<med_id>": "<drug_name>" }` for all resolved IDs.
7. **Return result** – Output the dictionary (or, if the caller expects a list, return the list of names in the same order as the original `MedicationRequest` list using the mapping).

## Checks
- Confirm that at least one `medicationReference` was found; otherwise return an empty dictionary.
- Verify each fetched resource is of type `Medication` and contains a `code` element.
- Ensure the extracted name is a non‑empty string; if not, use the ID as a placeholder.
- The final output must be a plain JSON object or list with no extra explanatory text.

## Avoid
- Returning the entire `Medication` resource; only the human‑readable name is needed.
- Leaving any IDs unresolved; always perform a fetch call for each unique ID.
- Assuming the name is always in `medicationCodeableConcept`; this skill is only for `medicationReference` cases.
