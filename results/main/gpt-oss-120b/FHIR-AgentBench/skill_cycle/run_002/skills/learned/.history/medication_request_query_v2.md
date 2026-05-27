---
description: Extend to handle queries listing multiple alternative drug names with
  optional date, route, or encounter filters.
name: medication_request_query
provenance:
  baseline_fixes: 2
  baseline_regressions: 5
  epoch: 1
  failure_mode: missing_prescription_query
  fixes: 4
  parent_version: 1
  probe_score: 5
  regressions: 2
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 00c6c1102d545178bf7380f3
  update_cycle: 0
tags: []
version: 2
---

## When to use
You must invoke this skill when a question asks whether **any** of several listed medications (e.g., "docusate sodium, glucose gel, or heparin") were prescribed or administered for a patient, possibly constrained by a date range, route, or specific encounter scope.

## Procedure
1. **Identify patient** – Extract the patient identifier from the question and resolve it to the FHIR patient ID.
2. **Parse temporal filter** – Detect explicit date ranges (e.g., "since 2157", "between 05/2137 and 06/2137"). If none are found, treat the time window as unbounded.
3. **Extract drug name list** –
   - Split the medication phrase on commas, the words "or" / "and", semicolons, or parentheses.
   - Trim whitespace and normalize each token to lower‑case.
   - Discard empty tokens.
4. **Parse optional route filter** – Detect mentions of a route (e.g., "via iv drip", "oral", "ng") and normalize.
5. **Parse optional encounter scope** – Recognize phrases such as "first hospital encounter", "last ICU visit", etc., and resolve the relevant encounter IDs using the existing encounter‑scope logic.
6. **Retrieve resources** – Call `get_resources_by_patient_fhir_id` for both `MedicationRequest` and `MedicationAdministration`.
7. **Iterate over resources** for each retrieved item:
   - **Determine prescription/administration date** using the first available field in this order: `authoredOn`, `occurrenceDateTime`, `recordedDate`, `effectiveDateTime`, `effectivePeriod.start`.
   - Skip the resource if the date falls outside the parsed time window.
   - **Resolve medication name**:
     * If `medicationCodeableConcept` is present, take the first `coding.display`, `coding.code`, or the `text` field.
     * If only `medicationReference` is present, fetch the referenced `Medication` resource with `get_resources_by_resource_id` and extract its `code.coding[0].display`/`code`/`text`.
     * Normalize the obtained name to lower‑case.
   - **Match against drug list** – If the normalized medication name **contains** any of the extracted drug tokens, consider it a match.
   - **Apply route filter** (if present) by checking `dosageInstruction.route` coding/display for the same containment logic.
   - **Apply encounter scope** (if present) by confirming that the resource’s `encounter.reference` resolves to one of the previously identified encounter IDs (including child encounters via `partOf`).
   - If all applicable filters pass, mark the resource as a matching prescription.
8. **Aggregate results**:
   - If the question asks for existence ("Has ... been prescribed ...?"), answer **"Yes"** if any match exists, otherwise **"No"**.
   - If the question requests the earliest or latest prescription date, collect the matching dates and return the minimum or maximum respectively in ISO‑8601 format.
9. **Return answer** in the exact format required by the question.

## Checks
- Confirm the patient FHIR ID is valid and resources were retrieved.
- Verify that at least one drug token was extracted; if the list is empty, fall back to the original single‑drug logic.
- Ensure date parsing succeeded; if a date string cannot be parsed, ignore that resource.
- When using `medicationReference`, guarantee the referenced `Medication` resource is successfully fetched before name extraction.
- Validate that the final answer conforms to the expected type ("Yes"/"No" or ISO datetime string).

## Avoid
- Treating the conjunction "or" as part of a drug name.
- Missing matches because of partial names (e.g., matching "heparin" with "heparin sodium"). Use containment rather than exact equality.
- Ignoring route or encounter filters when multiple drug names are present.
- Returning a negative answer when a matching `MedicationReference` could not be resolved.
- Providing a date when the question only asks for a boolean existence.
