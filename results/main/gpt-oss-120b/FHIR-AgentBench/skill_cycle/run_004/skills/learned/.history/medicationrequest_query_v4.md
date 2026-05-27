---
description: Add medicationReference resolution and robust name extraction to MedicationRequest
  queries
name: medicationrequest_query
provenance:
  baseline_fixes: 5
  baseline_regressions: 1
  epoch: 3
  failure_mode: medication_reference_not_checked
  fixes: 5
  parent_version: 3
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - 01bc93ed00df686c5593006f
  - 047259e83745142834b50838
  - 08e4e46ffbf10a71b11cc538
  update_cycle: 0
tags: []
version: 4
---

## When to use
You must invoke this skill whenever a user asks about medications that appear in **MedicationRequest** resources and the query may involve:
- Presence/absence of a medication
- Counting prescriptions, distinct drug names, or doses
- Filtering by date, encounter, route, or dosage amount
- Any request that does **not** explicitly reference a **MedicationAdministration** or **Medication** resource but mentions medication names, routes, or amounts.
The skill should also trigger when the MedicationRequest uses a **medicationReference** instead of a **medicationCodeableConcept**.

## Procedure
1. **Fetch MedicationRequests** for the patient via `get_resources_by_patient_fhir_id`.
2. **Collect all medicationReference IDs** found in the retrieved MedicationRequests.
3. **Batch‑fetch the referenced Medication resources** using `get_resources_by_resource_id` for each unique ID.
4. **Build a lookup table** `med_id → name` where the name is taken from the Medication resource in this order:
   - First `code.coding[*].display`
   - Then `code.coding[*].code`
   - Then `code.text`
   - If still missing, use the Medication's `title` or `ingredient[*].itemCodeableConcept.coding[*].display` as a fallback.
5. **Iterate over each MedicationRequest** and resolve its medication name:
   - If `medicationCodeableConcept` exists, extract the name using the same priority as step 4.
   - Otherwise, look up the name in the table built in step 4 via `medicationReference.reference` (format `Medication/<id>`).
6. **Apply query‑specific filters** (date range, encounter linkage, route, dosage amount):
   - Parse `authoredOn` or `dateWritten` as ISO‑8601 dates.
   - For encounter filtering, compare `MedicationRequest.encounter.reference` against the set of target Encounter IDs.
   - **Route matching**: inspect each `dosageInstruction[*].route` – check `coding[*].display`, `coding[*].code`, and `text` case‑insensitively for the requested route string (e.g., "im", "iv drip", "po/ng").
   - **Dose extraction**: sum `doseAndRate[*].doseQuantity.value` and, if present, `dosageInstruction[*].doseQuantity.value`. Preserve units when required.
7. **Perform the requested aggregation**:
   - Presence → return "Yes"/"No".
   - Count → integer count of matching MedicationRequests.
   - Distinct drugs → set of resolved medication names, then return the count.
   - Total dose → numeric sum (optionally with unit).
   - Last/first prescription → sort by the parsed date and return the medication name (or full record as asked).
8. **Format the answer** exactly as the user expects (plain number, string, or phrase). Do not append extra commentary.

## Checks
- Verify that every MedicationRequest considered has a resolved medication name; if a name cannot be resolved, **exclude** that record and log a warning.
- Ensure dates are parsed without timezone offsets; compare using naive `datetime` objects.
- When filtering by route, normalise both the query term and the resource value with `lower().strip()` and collapse whitespace.
- If aggregating doses, confirm that all numeric values share the same unit; if units differ, either convert (if conversion is known) or return the sum with a generic "units" label.
- Confirm that the final answer type matches the question (e.g., integer for counts, string for names, float for amounts).

## Avoid
- Assuming every MedicationRequest contains `medicationCodeableConcept`; this was the root cause of the previous failures.
- Double‑counting the same medication when it appears in both `medicationCodeableConcept` and `medicationReference`.
- Matching routes on partial substrings that lead to false positives (e.g., matching "im" inside "timed"). Use whole‑word or exact‑match after normalisation.
- Returning `None` or placeholder strings like the raw reference ID; always attempt the lookup first.
- Including MedicationRequests that fall outside the requested time window or encounter scope.
- Adding extra explanatory text beyond the required answer format.
