---
description: Improve extraction of drug name from MedicationReference resources
name: resolve_medication_reference
provenance:
  baseline_fixes: 4
  baseline_regressions: 2
  epoch: 3
  failure_mode: medication_id_returned_instead_of_name
  fixes: 4
  parent_version: 1
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - 062575cdb38e709723edbb54
  - 065b726dbf86eb804accd168
  - 06b1eef22357320dc0f8a64a
  - 0a8c46b684e72300d29c18aa
  update_cycle: 1
tags: []
version: 2
---

## When to use
You must invoke this skill whenever you are processing a **MedicationRequest** that contains a `medicationReference` and you need the actual drug name (e.g., the question asks for the drug name, not the medication ID).

## Procedure
1. **Identify the reference** – read `medicationReference.reference` from the MedicationRequest. It should be of the form `Medication/<id>`.
2. **Fetch the Medication resource** – call `get_resources_by_resource_id` with `resource_type="Medication"` and the extracted `<id>`.
3. **Extract the drug name** using the following priority order:
   - If `Medication.code.coding` exists, return the first non‑empty `display` field.
   - If no `display`, return the first non‑empty `code` field from the same coding entry.
   - If `Medication.code.text` is present, use that.
   - If `Medication.code.coding` is empty but `Medication.code` itself has a `code` field, use it.
   - If none of the above yield a value, return `None`.
4. **Cache the result** – store the mapping `<med_id> -> drug_name` in a local dictionary for the duration of the current query to avoid duplicate fetches.
5. **Return** a dictionary `{ "med_name": <extracted_name>, "med_id": <id> }` (or just the name if the caller expects a plain string).

## Checks
- Verify that the fetched resource is of type **Medication**.
- Ensure the extracted name is a non‑empty string; if it is empty, treat it as a failure and fall back to `None`.
- Confirm that the returned value matches the expected answer format (plain drug name string, not the ID).
- If the Medication resource cannot be fetched or contains no identifiable name, raise a clear “name not found” flag so the caller can handle the missing data.

## Avoid
- Returning the medication ID instead of the drug name.
- Assuming `display` is always present; always apply the fallback chain.
- Making additional network calls for the same medication ID within a single query (use the cache).
- Ignoring errors from the FHIR server; handle missing resources gracefully.
