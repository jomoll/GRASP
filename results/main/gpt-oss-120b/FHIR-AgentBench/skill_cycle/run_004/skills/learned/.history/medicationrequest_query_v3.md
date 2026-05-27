---
description: 'Robust handling of MedicationRequest queries: presence, counts, distinct
  drugs, routes, doses, and encounter linking.'
name: medicationrequest_query
provenance:
  baseline_fixes: 2
  baseline_regressions: 9
  epoch: 1
  failure_mode: medicationrequest_not_queried
  fixes: 3
  parent_version: 2
  probe_score: 5
  regressions: 5
  triggering_sample_ids:
  - 01389011a3cea028b226b95b
  - 03d470fc8e41f5dd8568f771
  - 065b726dbf86eb804accd168
  - 0874a8eb9ae4f8b6bb50a1d4
  - 098b1301820b7d581a339d0f
  - 0ce9c8a93ef40fa209454a71
  update_cycle: 0
tags: []
version: 3
---

## When to use
You must use this skill whenever the user asks for any information that comes from **MedicationRequest** resources. This includes questions about:
- Whether a patient has been prescribed any medication (yes/no).
- How many prescriptions match a date range, route, or specific drug.
- The number of **distinct** drugs prescribed in a period or encounter.
- The **total dose** (sum of all doseQuantity values) for a drug or for all prescriptions.
- The **first/last** prescription overall or within a particular encounter (hospital, ICU, etc.).
- Prescriptions linked to a **specific encounter** (first hospital stay, last ICU stay, etc.).
- Any combination of the above (e.g., "total iv‑drip dose of insulin during the first hospital encounter").

## Procedure
1. **Retrieve resources**
   - Call `get_resources_by_patient_fhir_id` for `MedicationRequest`.
   - If the query may involve encounter scoping, also retrieve `Encounter` (and optionally `Medication` for name resolution).
2. **Parse temporal constraints**
   - Detect absolute dates, month/year strings (e.g., `05/2150`), relative phrases (`this year`, `last month`).
   - Convert them to inclusive `start` and exclusive `end` `datetime` objects.
3. **Identify target encounters (if needed)**
   - Hospital encounters: identifier system containing `encounter-hosp` (case‑insensitive) **or** class code `IMP`.
   - ICU encounters: identifier system containing `encounter-icu` **or** class code `ICU`.
   - Sort encounters by `period.start` to find **first** or **last** as requested.
   - Build a set `target_encounter_ids` that includes the chosen encounter **and** any child encounters referenced via `partOf`.
4. **Filter MedicationRequests**
   - **Date filter**: keep only those where `authoredOn` or `dateWritten` falls within the computed window.
   - **Encounter filter** (if an encounter scope was identified): keep only requests whose `encounter.reference` ends with an ID in `target_encounter_ids`.
   - **Route filter**: for each request, collect all route strings from `dosageInstruction[*].route` (coding.display, coding.code, route.text). Normalize (lower‑case, trim whitespace). Keep the request if any normalized route matches the requested route (e.g., `iv drip`, `ng`, `enteral`).
   - **Medication name filter**: resolve the drug name using the following precedence:
     a. `medicationCodeableConcept.coding[*].display` or `.code`.
     b. `medicationCodeableConcept.text`.
     c. If `medicationReference` is present, load the referenced `Medication` resource and use `Medication.code.coding[*].display`/`.code` or `Medication.code.text`.
     Normalize the name and compare to the target (allow partial matches, case‑insensitive).
5. **Compute the requested metric**
   - **Existence**: answer "Yes" if any request survived the filters, else "No".
   - **Count**: `len(filtered_requests)`.
   - **Distinct drug count**: build a `set` of resolved drug names from the filtered requests and return its size.
   - **Total dose**:
        * For each request, iterate over `dosageInstruction[*].doseAndRate[*].doseQuantity` (or legacy `doseQuantity`).
        * Extract `value` and `unit`.
        * Sum all `value`s **only when the unit matches** the unit of the first dose (otherwise ignore mixed units to avoid incorrect aggregation).
        * Return the sum followed by the unit (e.g., `1250 mg`).
   - **First / Last prescription**: sort filtered requests by `authoredOn` (fallback to `dateWritten`). Return the earliest or latest request’s drug name and date.
6. **Format the answer** exactly as the user expects:
   - Boolean answers as `Yes`/`No`.
   - Numeric answers as plain integers.
   - Dose answers as `<value> <unit>`.
   - Date‑time answers in the original ISO‑8601 string.
   - When multiple values are required (e.g., list of drugs), join with commas.

## Checks
- Confirm that at least one `MedicationRequest` resource was retrieved; if none, answer "No" for existence queries.
- Verify that any date strings parsed successfully; if a date cannot be parsed, ignore that request.
- Ensure the encounter filter correctly includes child encounters via `partOf`.
- When summing doses, verify that all selected doses share the same unit; if units differ, report the sum for each unit separately or fall back to "Cannot aggregate mixed units".
- Validate that the final answer matches the requested type (boolean, integer, string, or `<value> <unit>`).

## Avoid
- **Missing route filtering** – do not rely only on `medicationCodeableConcept`; always inspect `dosageInstruction.route`.
- **Duplicate drug counting** – when computing distinct drugs, use the normalized name; do not count the same drug twice because it appears with different codes.
- **Ignoring child encounters** – always expand the encounter scope to include encounters referenced via `partOf`.
- **Partial date windows** – treat month specifications as the full calendar month, not a single day.
- **Mixed‑unit dose aggregation** – never add milligrams to units of "units"; either separate or abort with a clear message.
- **Assuming a single dosageInstruction** – some requests have multiple dosageInstructions; sum across all of them.
- **Returning raw Python objects** – always convert to plain text/number strings before replying.
