---
description: "Match medication names using case\u2011insensitive substring search\
  \ across MedicationRequest and Medication resources"
name: medication_name_substring_match
provenance:
  baseline_fixes: 3
  baseline_regressions: 2
  epoch: 5
  failure_mode: medication_name_exact_match_instead_of_substring
  fixes: 5
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 08e4e46ffbf10a71b11cc538
  - 09469e7ae520d7c2a28ad15f
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must trigger this skill whenever a question references a medication by name (e.g., "docusate sodium (liquid)", "glucose gel", "heparin flush") and the answer depends on whether that medication was prescribed, its dose, or quantity. The question may use partial names, extra qualifiers, or different casing, so an exact display‑string match is insufficient.

## Procedure
1. **Query required resources** – Ensure the agent has already fetched all `MedicationRequest` resources for the patient (and `Medication` resources if any `medicationReference` fields are present). If not, call `get_resources_by_patient_fhir_id` for those types before proceeding.
2. **Build a medication display map**
   - Iterate over all retrieved `Medication` resources.
   - For each resource, extract a display name from:
     - `code.coding[0].display` or `code.coding[0].code`
     - fallback to `code.text`
   - Store `med_id -> normalized_display` in a dictionary.
3. **Normalize target names**
   - From the user question, extract the medication name(s) mentioned.
   - Apply the same normalization to each target: trim whitespace, collapse multiple spaces to a single space, and lower‑case the string.
4. **Search MedicationRequests**
   - For each `MedicationRequest`:
     - Determine the medication name:
       - If `medicationCodeableConcept` is present, take the first `coding.display` or `coding.code`.
       - Else if `medicationReference` is present, look up the reference ID in the map built in step 2.
     - Normalize the obtained name using the same function as step 3.
     - **Substring match** – consider the request a hit if any normalized target string is a substring of the normalized medication name **or** the medication name is a substring of the target (covers cases where the target includes a qualifier).
5. **Apply additional filters** (if the question includes a date window, encounter scope, dosage field, etc.)
   - Parse dates (`authoredOn`, `occurrenceDateTime`, `effectivePeriod.start`, etc.) and keep only requests that satisfy the window.
   - If the question limits to a specific encounter, verify `MedicationRequest.encounter.reference` matches the encounter ID(s).
6. **Derive the answer**
   - For existence questions, return "Yes" if any hit, otherwise "No".
   - For dose/amount questions, collect the relevant field (`doseQuantity.value`, `dose_val_rx`, `dispenseRequest.quantity.value`, etc.) from the matching requests and compute the required aggregation (first, last, sum, count, etc.) as dictated by the question.
7. **Pass to answer format enforcement** – Let the existing `answer_format_enforcement` skill validate the final answer type.

## Checks
- Verify that at least one `MedicationRequest` (and optionally `Medication`) resource was retrieved before matching.
- Confirm the normalized target and candidate strings are non‑empty.
- Ensure any required date range, encounter ID, or dosage field is present; if missing, treat the request as non‑matching.
- The final answer must match the expected type (boolean, numeric, date string, list, or dict) inferred from the question.

## Avoid
- Do **not** rely on exact equality of display strings; this was the source of the failure.
- Do not ignore `medicationReference` links – always resolve them through the `Medication` map.
- Do not match on unrelated fields (e.g., `status`, `category`) unless the question explicitly asks for them.
- Do not return a default "No" when the required resources are missing; instead, let the agent raise a missing‑data error or defer to a higher‑level fallback.
