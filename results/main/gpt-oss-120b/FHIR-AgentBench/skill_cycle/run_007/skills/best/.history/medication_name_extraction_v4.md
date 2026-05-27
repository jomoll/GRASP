---
description: Resolve medicationReference IDs to names by fetching Medication resources
  and extracting display text.
name: medication_name_extraction
provenance:
  baseline_fixes: 2
  baseline_regressions: 2
  epoch: 16
  failure_mode: no_answer_returned
  fixes: 3
  parent_version: 3
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 00c6c1102d545178bf7380f3
  - 00fbe516569113decea8de73
  - 06b1eef22357320dc0f8a64a
  - 08e4e46ffbf10a71b11cc538
  - 09469e7ae520d7c2a28ad15f
  update_cycle: 0
tags: []
version: 4
---

## When to use
You should run this skill whenever the current question involves a MedicationRequest (or any medication‑related resource) and the request contains a `medicationReference` instead of a fully‑expanded `medicationCodeableConcept`.

## Procedure
1. Scan all retrieved `MedicationRequest` resources for a `medicationReference` field.
2. For each reference `Medication/<id>` that has not been fetched yet, call `get_resources_by_resource_id` with `resource_type="Medication"` and `resource_id="<id>"` and store the result in a local cache `med_cache` keyed by the medication id.
3. For each cached Medication resource, extract the medication name in the following priority order:
   - `code.coding[0].display` or `code.coding[0].code`
   - `product.form.text`
   - If the above are missing, look at the first ingredient: `product.ingredient[0].itemCodeableConcept.coding[0].display` or `.code`
4. Normalise the extracted name: strip whitespace, collapse internal spaces, and lower‑case it.
5. Attach the normalised name back to the originating `MedicationRequest` (e.g., add a temporary field `extractedMedicationName`).
6. Continue the pipeline with the enriched `MedicationRequest` objects.

## Checks
- Verify that the current task is a medication‑related query (question contains drug names, routes, doses, etc.).
- Ensure a `medicationReference` exists before attempting a fetch.
- Confirm that the fetched `Medication` resource is present in `retrieved_resources['Medication']` or was just fetched.
- The final name must be a non‑empty string; if none can be derived, leave the temporary field unset and let downstream skills handle the missing case.

## Avoid
- Re‑fetching the same Medication resource multiple times; always reuse the `med_cache`.
- Using unrelated fields such as `identifier` or `status` for the name.
- Returning a placeholder like "Unknown" when a proper name cannot be extracted; instead, leave the name unset so `no_data_handling` can trigger.
