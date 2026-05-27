---
description: "Resolve medicationReference IDs to Medication names and normalize them\
  \ for queries, **only when medication\u2011related data is present**. This prevents\
  \ the skill from running on unrelated tasks (e.g., observation queries) and avoids\
  \ side\u2011effects that break other samples."
name: medication_name_extraction
provenance:
  baseline_fixes: 3
  baseline_regressions: 4
  epoch: 15
  failure_mode: no_answer_returned
  fixes: 4
  parent_version: 2
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 00beff4406c2ee10ac9621fe
  - 047259e83745142834b50838
  - 065b726dbf86eb804accd168
  - 081ba7feccd490013f102984
  - 08b21636e8a003182b06159f
  - 09315d12007c47ae3fb400b6
  - 098b1301820b7d581a339d0f
  - 0b9e619bdb576876f002d49a
  update_cycle: 1
tags: []
version: 3
---

## When to use
Trigger this skill **only** when the current task involves medication data. Typical cues are:
- The user question contains medication‑related keywords such as "medication", "drug", "prescription", "dose", "tablet", "pill", "medic*", "pharmacy", etc.
- The retrieved FHIR resources include at least one `MedicationRequest` (or `MedicationStatement`).
If neither condition is met, the skill should exit without performing any work.

## Procedure
1. **Guard clause** – Verify that the current query is medication‑focused *and* that `MedicationRequest` resources have been retrieved. If not, return immediately with no changes to the context.
2. **Collect MedicationRequests** for the patient (already retrieved by a prior query).
3. For each `MedicationRequest`:
   - If `medicationCodeableConcept` exists, extract the first `coding.display` or `coding.code` and normalize it (lower‑case, collapse whitespace).
   - If `medicationReference` exists, parse the reference string (`Medication/<id>`).
4. **Fetch Medication resources** for any unique IDs collected using `get_resources_by_resource_id`.
5. From each fetched `Medication` resource, extract a human‑readable name in this order of preference:
   1. `code.coding[0].display`
   2. `code.coding[0].code`
   3. `product.form.text`
   4. First `product.ingredient.itemCodeableConcept.coding[0].display` or `.code`
   5. If none of the above are present, use the placeholder string **"Unknown medication"**.
6. Normalize the selected name (lower‑case, single spaces) and store a mapping `{MedicationRequest.id: medication_name}` in the skill’s local context for downstream lookup.
7. **Do not raise exceptions** – any missing `Medication` resource or unexpected structure should be logged with a warning and result in the placeholder name, not a hard error.

## Checks
- Ensure the guard clause correctly skips execution when the task is not medication‑related.
- Verify that at least one `MedicationRequest` was inspected before proceeding with fetching.
- Confirm every `medicationReference` ID either resolves to a fetched `Medication` or falls back to "Unknown medication" without breaking the workflow.
- Validate that the final normalized name is a non‑empty string before storing it.

## Avoid
- Running this skill for non‑medication queries (e.g., observation, lab, vital‑sign questions).
- Using the `MedicationRequest.id` as the medication name.
- Returning raw coding objects, IDs, or un‑normalized strings.
- Throwing uncaught exceptions that abort the overall agent run.
