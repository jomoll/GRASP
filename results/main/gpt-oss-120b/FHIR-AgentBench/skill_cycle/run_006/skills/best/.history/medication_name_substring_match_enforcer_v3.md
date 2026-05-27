---
description: Ensures medicationReference IDs are resolved to Medication resources
  before substring matching.
name: medication_name_substring_match_enforcer
provenance:
  baseline_fixes: 3
  baseline_regressions: 1
  epoch: 10
  failure_mode: no_answer_returned_from_processing
  fixes: 4
  parent_version: 2
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 0702bc77d929f78085010bb0
  - 09b1b086d491d385b6744dd6
  update_cycle: 0
tags: []
version: 3
---

## When to use
You should trigger this skill whenever a question asks whether a patient was prescribed a medication (or list of medications) using a substring of the drug name, and the prescription data may be stored in `MedicationRequest` resources that reference a `Medication` resource via `medicationReference`.

## Procedure
1. **Fetch required resources** – Confirm that `MedicationRequest` resources for the patient have already been retrieved (the `resource_query_precheck_medicationrequest` skill guarantees this). If any `Medication` resources referenced by those requests are missing, call `get_resources_by_resource_id` for each referenced `Medication` ID.
2. **Build a name lookup table**:
   - For each `MedicationRequest`:
     - Collect candidate names from `medicationCodeableConcept`:
       * Any `coding.display`, `coding.code`, and the `text` field (if present).
     - If the request contains `medicationReference`, retrieve the corresponding `Medication` resource and add its name candidates from `Medication.code.coding.display`, `Medication.code.coding.code`, and `Medication.code.text`.
   - Normalise every candidate name by:
     * Stripping surrounding whitespace,
     * Collapsing internal whitespace to a single space,
     * Converting to lower‑case.
3. **Process the query substrings**:
   - Normalise each medication name asked for in the user question using the same routine as above.
   - For each query substring, check if it is a substring of any candidate name (case‑insensitive) **or** if any candidate name is a substring of the query (to catch reversed order).
4. **Form the answer**:
   - If the original question expects a boolean (e.g., "Did patient X receive Y?"), return `true` if any match is found, otherwise `false`.
   - If the question asks for a list of medications, return a JSON‑compatible list of the matched medication names (original case as stored).

## Checks
- Verify that every `medicationReference` ID has a corresponding `Medication` resource; if a referenced medication cannot be fetched, log a warning and continue with the remaining data.
- Ensure the answer type matches the question (boolean vs. list of strings).
- Confirm that the final medication names are not empty strings before inclusion.

## Avoid
- Matching against the `MedicationRequest.id` or other identifiers instead of the actual drug name.
- Ignoring `Medication` resources referenced by `medicationReference` (the primary cause of missed matches).
- Performing case‑sensitive or whitespace‑sensitive comparisons that would miss valid matches.
- Returning raw FHIR objects; only return the required answer format.
