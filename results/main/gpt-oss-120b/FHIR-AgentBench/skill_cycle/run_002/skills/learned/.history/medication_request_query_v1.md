---
description: Query MedicationRequest (and MedicationAdministration) for a patient
  with filters on date, drug name, route, and encounter scope.
name: medication_request_query
provenance:
  baseline_fixes: 3
  baseline_regressions: 2
  epoch: 0
  failure_mode: missing_medication_request_query
  fixes: 4
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 0056cade81e16f20fe9fe322
  - 00beff4406c2ee10ac9621fe
  - 0266d6e5d007484e57bf12d6
  - 072f960a91e48e6fe38d81a1
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must trigger this skill whenever the user asks any question about **prescribed or administered medications** for a patient, such as:
- "Has patient X had any medication prescribed since 05/2137?"
- "Did patient X receive a prescription for clonidine patch, atorvastatin, or prasugrel on the first hospital visit?"
- "What was the name of the drug first prescribed via the IV drip route?"
- "How many unique drugs were prescribed in 04/this year?"
- Any request that mentions *prescribed*, *prescription*, *medication*, *drug*, *dose*, *route*, or asks for a count/list of drugs.

## Procedure
1. **Retrieve resources**
   - Call `get_resources_by_patient_fhir_id` for `MedicationRequest` (and also `MedicationAdministration` because some administrations are not captured as requests).
2. **Normalize helper functions**
   - `norm(s) = re.sub(r'\s+', ' ', (s or '').strip().lower())` for case‑insensitive, whitespace‑insensitive matching.
3. **Identify the relevant encounter (if required)**
   - If the question mentions *first/last hospital visit*, *first ICU visit*, etc., first query `Encounter` resources for the patient, filter by identifier system containing `encounter-hosp` (or class code `IMP` as fallback).
   - Sort by `period.start` to get the first or last encounter ID and keep a set of that encounter and any child encounters (`partOf` references ending with the parent ID).
4. **Filter MedicationRequest records**
   - **Date filter**: keep records where `authoredOn` or `occurrenceDateTime` (or `recordedDate`) is present and falls within the user‑specified window. Parse with `datetime.fromisoformat` (ignore timezone).
   - **Encounter filter**: if an encounter scope was determined, keep only requests where `encounter.reference` ends with one of the allowed encounter IDs.
   - **Drug name filter**: for each request, obtain the drug name:
     - Prefer `medicationCodeableConcept.coding[0].display` (or `text`).
     - If only a `medicationReference` is present, fetch the referenced `Medication` resource via `get_resources_by_resource_id` and use its `code.coding[0].display`.
     - Compare the normalized drug name to any user‑provided list (comma‑separated) using `norm`.
   - **Route filter**: examine each `dosageInstruction` entry; if a `route` element exists, check its `coding` displays or codes for the desired route (e.g., `iv`, `iv drip`, `po`, `ng`, `im`). Use regex word boundaries to avoid partial matches.
5. **Aggregate results** based on the question type:
   - **Existence/Yes‑No**: if any record survives the filters, answer `Yes`; otherwise `No`.
   - **Count of prescriptions**: return the length of the filtered list.
   - **Count of unique drugs**: build a `set` of normalized drug names and return its size.
   - **First/last prescribed drug**: sort surviving records by the date field and pick the earliest or latest; return the drug name (and optionally the date).
   - **List of drugs**: return a comma‑separated list of unique drug names, preserving original casing from the resource.
6. **Answer formatting**
   - Follow the exact format the user expects (e.g., boolean `Yes`/`No`, integer count, drug name string, ISO‑8601 datetime). Do not add extra commentary.

## Checks
- Verify that at least one `MedicationRequest` (or `MedicationAdministration`) was retrieved for the patient.
- Ensure the date field used (`authoredOn`, `occurrenceDateTime`, or `effectiveDateTime` for administrations) is parsed correctly and falls inside the requested window.
- Confirm that any encounter filtering uses the correct encounter IDs and includes child encounters when applicable.
- When matching drug names or routes, apply the `norm` function to both the resource value and the user‑provided term.
- Before answering, make sure the answer type matches the question (boolean, integer, string, or datetime).

## Avoid
- Forgetting to filter by the requested encounter (first/last hospital stay) and returning drugs from unrelated encounters.
- Ignoring the route requirement, which leads to false positives for drugs given via a different route.
- Using only `medicationReference` without dereferencing the `Medication` resource, resulting in missing drug names.
- Returning a list of all drugs when the user asked only for existence or a count.
- Mis‑parsing dates that include timezone offsets; always strip timezone before comparison.
- Performing a plain text search on the whole `MedicationRequest` JSON instead of the structured fields described above.
