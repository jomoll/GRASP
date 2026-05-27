---
description: Expand triggers and logic to handle counts, distinct drugs, routes, and
  dose aggregation in medication queries.
name: medicationrequest_query
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 0
  failure_mode: medicationrequest_not_queried
  fixes: 5
  parent_version: 1
  probe_score: 1
  regressions: 4
  triggering_sample_ids:
  - 02a069698a803a8419fa294c
  - 0814561e80d18ee7b5e8e214
  - 0c6cdc444ee911941bfd23f0
  - 0ceee1a85a040c4d57c27a09
  update_cycle: 1
tags: []
version: 2
---

## When to use
You must activate this skill whenever the user asks **any** medication‑related question, including but not limited to:
- "how many / count / number of *medications / drugs / prescriptions* …" (e.g., distinct, unique, total)
- Queries that request the *first*, *last*, *most recent*, *earliest* medication in a given encounter or time window
- Requests that mention a **specific medication name** (any case/whitespace variation) and ask whether it was prescribed, when it was first/last prescribed, or how many times
- Questions that refer to a **route of administration** (e.g., iv, iv drip, po, po/ng, im, sc, ih, ng, inhalation, subcutaneous, intramuscular, etc.)
- Requests that ask for **dose aggregation** (total dose, sum of doseQuantity, amount prescribed) across a period or encounter
- Any query that includes a time constraint (month/year, "since", "last X months", specific dates) or an encounter scope (hospital, ICU, ER, first/last visit)
If none of the above patterns appear, do not fire this skill.

## Procedure
1. **Retrieve resources**
   - Call `get_resources_by_patient_fhir_id` for `MedicationRequest`.
   - If the query may involve medication names via a reference, also call `get_resources_by_patient_fhir_id` for `Medication`.
2. **Parse the user request**
   - Detect a time window (e.g., "since 04/2023", "in 11/2161", "last month", explicit dates).
   - Detect an encounter scope (e.g., "last hospital encounter", "first ICU visit", "last ER visit").
   - Detect a route keyword (iv, iv drip, po, po/ng, im, sc, ih, ng, inhalation, subcutaneous, intramuscular). Use case‑insensitive substring matching on `dosageInstruction.route.coding.display`, `dosageInstruction.route.coding.code`, and `dosageInstruction.route.text`.
   - Detect medication name(s) – normalize both the query term and any medication display/text by lower‑casing and collapsing whitespace.
   - Detect the operation type: **existence**, **count**, **distinct count**, **first/last name**, **dose sum**, **dose list**, **boolean presence**.
3. **Filter by date**
   - For each `MedicationRequest`, use `authoredOn` if present, otherwise `dateWritten`.
   - Keep only those whose datetime falls inside the parsed window (inclusive).
4. **Filter by encounter** (if requested)
   - Resolve the encounter reference (`MedicationRequest.encounter.reference`).
   - If an encounter scope is specified, fetch `Encounter` resources, identify the appropriate encounter (first, last, ICU, hospital, ER) using identifiers or class codes, and keep only medication requests linked to that encounter (including child encounters via `partOf`).
5. **Filter by route** (if requested)
   - Keep only requests where any `dosageInstruction[i].route` matches the requested route pattern.
6. **Resolve medication name**
   - Prefer `medicationCodeableConcept.coding.display` → `medicationCodeableConcept.text`.
   - If `medicationReference` is present, look up the corresponding `Medication` resource and use its `code.coding.display`, `code.coding.code`, or `identifier` with a "medication‑name" system.
   - Normalise the final name (lower‑case, trim spaces).
7. **Execute the operation**
   - **Existence / Yes‑No**: return "Yes" if any record remains, otherwise "No".
   - **Count**: return the integer length of the filtered list.
   - **Distinct count**: build a `set` of normalised medication names and return its size.
   - **First / Last medication name**: sort remaining records by date (ascending for first, descending for last) and return the medication name of the first element.
   - **Dose aggregation**: sum all `dosageInstruction[i].doseAndRate[j].doseQuantity.value` (numeric) across the filtered records; if a custom field like `dose_val_rx` exists, include it.
   - **List of names**: return a JSON‑array of distinct medication names (alphabetically sorted) if the query explicitly asks for the list.
8. **Format the answer**
   - Return plain text for Yes/No, integer for counts, numeric (float) for dose sums, or a single medication name string for name queries. Do not include extra debugging output.

## Checks
- Verify that at least one `MedicationRequest` was retrieved; if none, answer "No" for existence queries or `0` for count queries.
- Ensure the date filter (if any) was applied correctly; if the user supplied a month/year without a day, treat the whole month as inclusive.
- When an encounter scope is required, confirm that the identified encounter exists; if not, respond with a clear statement (e.g., "No hospital encounter found").
- For route matching, confirm that the route string was found in any coding/display/text field; avoid false positives from unrelated text.
- When aggregating doses, confirm that the extracted value is numeric; skip non‑numeric entries.
- Ensure the final answer matches the expected type (Yes/No, integer, float, or string) and contains no extra characters.

## Avoid
- Triggering on queries that do **not** mention medication concepts (e.g., ICU length of stay, PO₂ values, weight, lab tests unrelated to medication).
- Double‑counting the same medication when it appears with different codes; always deduplicate by normalised display/name for distinct‑count operations.
- Ignoring `medicationReference` resources; always resolve them when present.
- Matching route substrings that are part of unrelated words (e.g., "im" inside "time"); require the substring to appear as a whole word or within a coding/display field.
- Returning a list when the user asked for a single value or count.
- Forgetting to include child encounters linked via `partOf` when an encounter scope is specified.
