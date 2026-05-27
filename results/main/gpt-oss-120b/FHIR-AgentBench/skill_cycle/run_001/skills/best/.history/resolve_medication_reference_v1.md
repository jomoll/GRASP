---
description: Fetch and use the referenced Medication resource when a MedicationRequest
  uses medicationReference.
name: resolve_medication_reference
provenance:
  baseline_fixes: 5
  baseline_regressions: 4
  epoch: 1
  failure_mode: medication_reference_not_resolved
  fixes: 6
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 07bde541ff2932869ecb4912
  - 08e4e46ffbf10a71b11cc538
  update_cycle: 1
tags:
- medication
- reference
- resolution
version: 1
---

## When to use
You should invoke this skill whenever a **MedicationRequest** (or any resource that contains a `medicationReference`) is being inspected for the medication name or dosage, and the request does **not** contain a `medicationCodeableConcept` or its `medicationCodeableConcept` lacks a usable display.

## Procedure
1. **Detect a medicationReference** – In the current `MedicationRequest` record, check if the field `medicationReference.reference` exists and starts with `Medication/`.
2. **Extract the Medication ID** – Split the reference on `/` and keep the last segment as the Medication resource ID.
3. **Retrieve the Medication resource** – Call `get_resources_by_resource_id` with:
   ```json
   {"resource_type": "Medication", "resource_id": "<extracted_id>"}
   ```
   Cache the result for the duration of the query so that multiple requests referencing the same Medication do not cause duplicate calls.
4. **Parse the medication name** – From the retrieved Medication resource, locate the name in one of the following places (in order of preference):
   - `code.coding[0].display`
   - `code.coding[0].code`
   - `code.text`
   If none of these fields exist, treat the name as unknown and skip the record.
5. **Normalize the name** – Apply the same normalisation used for other medication strings (lower‑case, collapse whitespace) so that matching against target strings works reliably.
6. **Continue the original logic** – Use the resolved and normalized medication name wherever the skill originally expected a display value (e.g., checking against a list of target medications, counting doses, etc.).

## Checks
- Verify that the `medicationReference` string is well‑formed (`Medication/<id>`). If malformed, log and ignore the record.
- Ensure the fetched Medication resource exists; if the API returns empty, treat the medication as unresolved and do not count it.
- After resolution, confirm that the extracted name is a non‑empty string before proceeding to matching or aggregation.
- When aggregating doses, confirm that the dose field (`doseQuantity`, `dose_val_rx`, or similar) is numeric before adding.
- The final answer must respect the expected format of the original query (e.g., list of medication names, total dose number, boolean presence).

## Avoid
- Assuming the medication name is always present in `medicationCodeableConcept`; this skill specifically handles the case where only a reference is provided.
- Performing a full search of all Medication resources; only the referenced ID should be fetched.
- Returning a medication name when the reference could not be resolved – instead, skip that record and continue.
- Double‑counting doses by fetching the same Medication resource multiple times; cache results per ID within a single query.
