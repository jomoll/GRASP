---
description: Resolve all medicationReference IDs in a list of MedicationRequest resources
  to drug names for downstream queries.
name: resolve_medication_reference_batch
provenance:
  baseline_fixes: 0
  baseline_regressions: 1
  epoch: 11
  failure_mode: no_answer_returned
  fixes: 1
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 047259e83745142834b50838
  - 059ed55281d42669ad25d514
  - 0ceee1a85a040c4d57c27a09
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must invoke this skill whenever the user asks about drugs ordered/prescribed and you have retrieved `MedicationRequest` resources that contain a `medicationReference` (instead of a fully populated `medicationCodeableConcept`). Typical triggers are questions like *"Was acetaminophen ordered?"* or *"What was the last drug prescribed via IV?"* where the medication name is not directly present in the `MedicationRequest`.

## Procedure
1. **Collect referenced IDs** – Iterate over the provided `MedicationRequest` list and gather every distinct `medicationReference.reference` value that matches the pattern `Medication/<id>`.
2. **Fetch Medication resources** – For each unique `<id>` call `get_resources_by_resource_id` with `resource_type="Medication"` and `resource_id=<id>`. Store the returned resource.
3. **Extract a display name** for each fetched Medication:
   - Prefer `code.coding[*].display` (first non‑empty).
   - If no display, fall back to `code.coding[*].code`.
   - If still missing, use `code.text` or the first identifier `value` whose `system` contains the word `medication-name`.
   - Normalise the name to lower‑case and strip surrounding whitespace.
4. **Build a mapping** `med_id → name`.
5. **Annotate the MedicationRequest list** – For each `MedicationRequest` that had a `medicationReference`, add a new field `resolvedMedicationName` containing the name from the map (or `null` if resolution failed).
6. **Return** the enriched list of `MedicationRequest` objects (you may drop the original `medicationReference` if you wish) so that subsequent skills can filter by drug name.

## Checks
- Verify that every `medicationReference` follows the `Medication/<id>` pattern; ignore malformed entries.
- Confirm that each fetched `Medication` resource actually contains a name; if not, record `null` and continue.
- Ensure that the final answer the agent produces is a plain scalar (e.g., "Yes", "No", or the drug name) – do not output the full resource objects.
- If the user’s query is time‑bound, make sure to preserve the original `authoredOn`/`occurrenceDateTime` fields for later date filtering.

## Avoid
- Assuming that `medicationCodeableConcept` is always present – this skill is only for the reference case.
- Making additional network calls for IDs that have already been resolved in the current turn.
- Returning the entire `Medication` resource; only the human‑readable name is needed.
- Forgetting to normalise case and whitespace, which leads to missed matches when comparing to the user’s drug list.
