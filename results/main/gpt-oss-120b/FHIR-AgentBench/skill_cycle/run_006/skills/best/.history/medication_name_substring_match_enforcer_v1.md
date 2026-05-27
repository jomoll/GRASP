---
description: "Matches medication names by substring (case\u2011insensitive) instead\
  \ of exact equality."
name: medication_name_substring_match_enforcer
provenance:
  baseline_fixes: 2
  baseline_regressions: 2
  epoch: 5
  failure_mode: medication_name_exact_match_used_instead_of_substring
  fixes: 5
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 00c6c1102d545178bf7380f3
  - 05a9aa5bb494b962444ac354
  update_cycle: 1
tags: []
version: 1
---

## When to use
Trigger this skill whenever a question asks *if* a medication (or a list of medications) **has been prescribed** and the medication name in the query may appear as a substring of the recorded name, e.g. "docusate sodium (liquid)", "glucose gel", "heparin", "acetaminophen", or any other drug name where the FHIR resource may store a longer display string.

## Procedure
1. **Fetch resources** – Ensure `MedicationRequest` resources for the patient are already retrieved (use `resource_query_precheck_medicationrequest` if needed). Also fetch `Medication` resources if any `MedicationReference` fields are present.
2. **Build a name map** – For each `Medication` resource, collect all possible textual identifiers:
   - `code.coding[*].display`
   - `code.coding[*].code`
   - `code.text`
   - `product.form.coding[*].display`
   - `product.form.text`
   Store them lower‑cased and stripped of excess whitespace.
3. **Normalize query targets** – For each medication name mentioned in the user question, apply the same normalization (lower‑case, collapse multiple spaces to a single space, strip).
4. **Iterate MedicationRequests**:
   - Determine the prescription date (`authoredOn` or `occurrenceDateTime`). Apply any date filter supplied by the question.
   - Gather candidate names from the request:
     * From `medicationCodeableConcept.coding[*].display` and `medicationCodeableConcept.text`.
     * If `medicationReference` is present, look up the corresponding `Medication` id in the name map and add all its collected names.
   - Normalize each candidate name the same way as step 3.
   - **Substring check** – Consider the medication a match if **any normalized query target appears as a substring** of any normalized candidate name **or** any normalized candidate name appears as a substring of the query target (covers cases where the stored name is longer, e.g., "Docusate Sodium 100 mg/5 ml (Liquid)").
5. **Aggregate result** – If at least one `MedicationRequest` satisfies the substring condition (and any temporal constraints), set answer = `True`; otherwise `False`.
6. **Return** – Output the boolean answer directly (the `answer_boolean_format_enforcer` will later enforce correct type).

## Checks
- Verify that the resource type is `MedicationRequest` (and optionally `Medication`).
- Confirm that date filters (if any) are applied using UTC‑aware `datetime` objects.
- Ensure the final answer is a Python `bool` (not a string).
- Validate that at least one medication name was extracted; if none are found, treat as `False` rather than error.

## Avoid
- Do not require exact equality of normalized strings; this is the exact problem this skill fixes.
- Do not match on unrelated fields such as dosage or route – only medication name displays.
- Do not ignore `MedicationReference` look‑ups; missing them would cause false negatives.
- Do not overlook case or whitespace differences – always normalize before comparison.
