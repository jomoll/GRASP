---
description: Guarantee that every needed FHIR resource type is queried before any
  answer is derived.
name: require_fhir_query_before_answer
provenance:
  baseline_fixes: 4
  baseline_regressions: 2
  epoch: 4
  failure_mode: missing_fhir_query_before_answer
  fixes: 5
  parent_version: 4
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - 00fbe516569113decea8de73
  - 017d9aef746962d1c3d9d52e
  - 01bb1845215fb7cc77678534
  - 01c02f4b897bb8192e16bd1d
  - 02759807d268a649ffbc56e0
  - 02c15c7a4faad2a32636fac7
  - 059ed55281d42669ad25d514
  - 06c9202911fa52427beba085
  - 0814561e80d18ee7b5e8e214
  - 09469e7ae520d7c2a28ad15f
  update_cycle: 1
tags: []
version: 5
---

## When to use
You must trigger this skill for any question that references patient data such as lab/observation results, medications, prescriptions, procedures, encounters, or discharge information. Typical patterns include keywords like *test*, *lab*, *measurement*, *value*, *prescribed*, *medication*, *drug*, *dose*, *procedure*, *surgery*, *visit*, *admission*, *encounter*, *discharge*, etc.

## Procedure
1. **Parse the question** to identify all FHIR resource types that could contain the answer:
   - Observation for lab tests, vital signs, measurements.
   - MedicationRequest for prescriptions or orders.
   - MedicationAdministration for administered drugs.
   - Medication for drug details when a reference must be resolved.
   - Encounter for visits, admissions, discharges, ICU/ER flags.
   - Procedure for surgeries or interventions.
2. **Check the current `retrieved_resources` dictionary** for each required type.
3. For any missing type, **issue a FHIR query** using the tool:
   ```json
   {"resource_type": "<TYPE>", "patient_fhir_id": "<PATIENT_ID>"}
   ```
   Replace `<TYPE>` with the missing resource type and `<PATIENT_ID>` with the patient’s FHIR ID extracted from the context.
4. After each query, **merge the newly fetched resources** into `retrieved_resources`.
5. **Re‑evaluate** the question with the now‑complete resource set before proceeding to any further reasoning or answer generation.
6. If after querying a required type the result set is empty, record that the data is unavailable and let downstream logic return an appropriate “No data” or `None` answer.

## Checks
- Verify that for every inferred resource type the `retrieved_resources` entry exists and is a list (even if empty).
- Ensure at least one query has been performed for each required type before any answer is computed.
- Confirm that the patient FHIR ID used in the query matches the ID supplied in the prompt.
- After querying, double‑check that the resources contain the fields needed for later extraction (e.g., `code.coding.display`, `effectiveDateTime`, `valueQuantity`).

## Avoid
- Answering before all necessary FHIR queries have been executed.
- Assuming a resource type is present just because another type was queried.
- Skipping a query because the question mentions a date range but not the resource type explicitly.
- Re‑using stale `retrieved_resources` from a previous question without resetting or re‑querying missing types.
