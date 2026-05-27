---
description: "Handles any medication\u2011related question (presence, count, distinct,\
  \ dosage sum, route, first/last) for a patient."
name: medication_query
provenance:
  baseline_fixes: 3
  baseline_regressions: 6
  epoch: 0
  failure_mode: no_answer_returned_after_query
  fixes: 4
  probe_score: 6
  regressions: 1
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 01389011a3cea028b226b95b
  - 0424a90b6986dc6ca2da8b3b
  - 081ba7feccd490013f102984
  - 09469e7ae520d7c2a28ad15f
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must activate this skill whenever the user asks about **medications, drugs, prescriptions, or orders** for a patient. Typical triggers include:
- "Has patient X been given Y?"
- "Did patient X receive any medication in <date range>?"
- "How many distinct drugs were prescribed during the first hospital encounter?"
- "What was the total/first/last dose of <drug> (via <route>) in <encounter or date range>?"
- Any query that mentions a drug name, a route (e.g., iv, po, ih, sc, ng, drip), dosage, count, or distinct‑medication statistics.

## Procedure
1. **Retrieve resources**
   - Call `get_resources_by_patient_fhir_id` for `MedicationRequest` (and optionally `MedicationAdministration` if the query mentions administrations).
   - If any `MedicationRequest` contains a `medicationReference`, fetch the referenced `Medication` resources with `get_resources_by_resource_id` to resolve the display name.
2. **Normalize drug names**
   - For each request, build a list of candidate names from:
     - `medicationCodeableConcept.text`
     - `medicationCodeableConcept.coding[*].display`
     - Resolved `Medication` `code.coding[*].display` or `code.coding[*].code`
   - Apply `norm = lambda s: re.sub(r"\s+", " ", (s or "").strip().lower())` to each name.
3. **Apply query‑specific filters**
   - **Date range**: keep requests where `authoredOn` or `dateWritten` (parsed with `datetime.fromisoformat`) falls inside the user‑specified start/end (inclusive). If no range is given, keep all.
   - **Encounter scope**: if the question mentions "last hospital encounter", "first hospital visit", etc., first locate the relevant `Encounter` resources, determine the appropriate encounter ID(s), and keep only requests whose `encounter.reference` ends with one of those IDs.
   - **Drug name filter**: keep requests where any normalized candidate name contains (or equals) the normalized target drug term(s).
   - **Route filter**: if a route is specified, examine each request’s `dosageInstruction[*].route.coding[*].display` and `.code`. Keep the request if any normalized route matches the target (e.g., "iv", "po", "ih", "sc", "ng", "drip").
4. **Extract answer data**
   - **Presence / Yes‑No**: if the user only asks whether a drug was prescribed, return "Yes" if any request survived the filters, else "No".
   - **List of drug names**: return a sorted list of the distinct normalized drug names that matched.
   - **Count**: return the integer count of matching requests.
   - **Distinct count**: build a set of unique identifiers (`medicationReference` URIs or the normalized drug name) and return its size.
   - **Dosage aggregation**:
     - For each matching request, iterate `dosageInstruction[*].doseAndRate[*].doseQuantity.value` (ignore missing or non‑numeric values).
     - If the query asks for *total* dose, sum all values.
     - If it asks for *first* or *last* dose, sort the requests by `authoredOn` (or by the effective date in the associated `MedicationAdministration` if available) and pick the earliest or latest value.
   - **Route‑specific dosage**: apply the same aggregation after the route filter.
5. **Format the answer** according to the question type (yes/no, integer, list, or numeric total). Ensure the answer is a plain value without extra text.

## Checks
- Verify that at least one `MedicationRequest` (or `MedicationAdministration`) resource was retrieved; if none, answer "No" for presence queries or `0` for count/dosage queries.
- Confirm that all date strings are successfully parsed; skip any that cannot be parsed.
- When an encounter scope is required, ensure the target encounter(s) were identified; if not, fall back to the whole patient history.
- Ensure dosage units are consistent (e.g., all in the same unit) before summing; if units differ, convert if conversion data is available, otherwise return the sum with a note that units were mixed (outside the skill’s scope).
- The final answer must match the expected format: `Yes`/`No`, a plain integer, a plain list of strings (JSON‑serializable), or a numeric value.

## Avoid
- **Ignoring `medicationReference`** – always resolve it to obtain the medication name.
- **Exact‑string matching only** – always normalize and allow partial matches after normalization.
- **Counting the same prescription twice** – deduplicate by reference or by normalized drug name when a distinct‑count is requested.
- **Including doses from unrelated routes** – apply the route filter before dosage aggregation.
- **Returning timestamps or full resource objects** – only return the concise answer as specified.
- **Overlooking the last hospital encounter** – correctly identify the encounter by the `encounter-hosp` identifier or the `class.code == "IMP"` fallback.
