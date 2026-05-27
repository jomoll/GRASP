---
description: "Extract human\u2011readable medication names, preferring display fields\
  \ and resolving references."
name: medication_name_extraction_preference
provenance:
  baseline_fixes: 6
  baseline_regressions: 2
  epoch: 7
  failure_mode: fhir_resource_wrong_field_extracted
  fixes: 6
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 01bc93ed00df686c5593006f
  - 05bb819666668fc43bad2666
  - 0a8c46b684e72300d29c18aa
  - 0b9e619bdb576876f002d49a
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should invoke this skill whenever a question asks for the name of a medication that was prescribed (MedicationRequest) or recorded (Medication) and the answer may involve a `medicationReference` or a `medicationCodeableConcept`. Typical patterns include:
- "What drug was prescribed last time?"
- "Which medication was given via the iv route?"
- Any query that expects a drug **title** rather than an internal code or identifier.

## Procedure
1. **Query required resources**
   - Use `get_resources_by_patient_fhir_id` for `MedicationRequest` and `Medication` (or the specific encounter if the question limits to an encounter).
2. **Build a Medication ID → name map**
   - For each `Medication` resource:
     1. If `code.coding[0].display` exists, use it.
     2. Else if `code.coding[0].code` exists, use it.
     3. Else if `code.text` exists, use it.
     4. Normalise the chosen string (strip whitespace, collapse internal spaces, keep original case for the final answer).
   - Store the result in a dictionary keyed by the Medication resource `id`.
3. **Extract the name from each MedicationRequest**
   - If `medicationCodeableConcept` is present, apply the same priority order as above (display → code → text).
   - If `medicationReference` is present, extract the referenced Medication `id` (the part after `Medication/`) and look it up in the map built in step 2.
   - If both fields are missing, fall back to any `dosageInstruction` text that may contain a drug name (optional, low‑confidence).
4. **Select the record required by the question** (e.g., most recent, first, by route, by date range, etc.).
5. **Return the extracted name** exactly as stored (do not further transform to uppercase or lowercase unless the question explicitly asks).

## Checks
- Verify that at least one `MedicationRequest` (or `Medication`) was retrieved; if none, answer `None` or a suitable “No medication found” message.
- Confirm that the extracted name contains at least one alphabetic character (`[A-Za-z]`). If the candidate is purely numeric (e.g., `55390000401`), discard it and continue searching for the next best match.
- Ensure the final answer type is a **string** (single medication title). If the question expects a list, aggregate distinct names after applying this extraction logic.
- Validate that any date/encounter filters mentioned in the question have been applied **before** name extraction.

## Avoid
- Returning raw identifiers, codes, or numeric IDs that appear in `Medication.id` or `Medication.code.coding[0].code` when a human‑readable display name is available.
- Using the `MedicationRequest.medicationReference` string itself (e.g., `Medication/12345`) as the answer.
- Ignoring the priority order; always prefer `display` over `code` and `code` over `text`.
- Answering before confirming that the required resource types have been queried (this skill should be used together with `require_fhir_query_before_answer`).
