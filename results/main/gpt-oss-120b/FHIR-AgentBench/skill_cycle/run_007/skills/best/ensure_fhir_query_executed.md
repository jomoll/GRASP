---
description: "Guarantee a relevant FHIR query is performed before answering any patient\u2011\
  data question."
name: ensure_fhir_query_executed
provenance:
  baseline_fixes: 1
  baseline_regressions: 4
  epoch: 0
  failure_mode: no_fhir_query_executed
  fixes: 4
  probe_score: 3
  regressions: 4
  triggering_sample_ids:
  - 000f58d3abb4ad76b2ebc35c
  - 00fbe516569113decea8de73
  - 0565efc9f6e08966694b0d93
  - 05708c73dfad0a3f4781563a
  - 0577ee51b3ad3c9fcf8fbbae
  - 062575cdb38e709723edbb54
  - 08e4e46ffbf10a71b11cc538
  - 0925d99c93fdf4626caf71cc
  - 0ce9c8a93ef40fa209454a71
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must trigger this skill whenever the user asks for any patient‑specific information that depends on FHIR resources, such as:
- Counts or dates of hospital visits (Encounter)
- Laboratory or vital‑sign values (Observation)
- Medication prescriptions or administrations (MedicationRequest, MedicationAdministration)
- Procedures performed (Procedure)
- Any question that includes time windows, encounter types, routes, or specific test names.
If the question contains keywords like *visit, admission, discharge, encounter, hospital, ICU, observation, lab, test, measurement, value, medication, prescription, drug, procedure, microbiology*, you should verify a query has been executed.

## Procedure
1. **Parse the question** to identify the primary FHIR resource type needed (Encounter, Observation, MedicationRequest, MedicationAdministration, Procedure, etc.) and any required filters (date range, encounter identifier, route, test name).
2. **Inspect `retrieved_resources`** (the tool‑provided cache) for the identified resource type.
   - If the list is present and non‑empty, proceed to the next step.
   - If it is missing or empty, **invoke the appropriate tool**:
     ```json
     {"resource_type": "<Resource>", "patient_fhir_id": "<patient_fhir_id>"}
     ```
     where `<Resource>` is the type determined in step 1.
3. **Re‑inspect** the cache after the tool call. If the required resources are still absent, **abort the answer** and return a clear message like:
   > "No <Resource> data found for patient <id> matching the requested criteria."
4. Once data is present, **hand off** to the downstream skill that performs filtering, aggregation, or formatting.

## Checks
- Confirm that at least one resource of the needed type is now in `retrieved_resources`.
- Ensure the resources belong to the patient referenced in the question (match the patient FHIR ID).
- Verify that any date‑range or encounter‑type constraints mentioned in the question will be applied later (do not answer before those filters are executed).
- The final answer must be produced only after a successful query; otherwise, return the abort message.

## Avoid
- Providing an answer based on assumptions or hard‑coded defaults when no data has been fetched.
- Skipping the query step because the question seems simple; even a count of visits requires an Encounter query.
- Ignoring time windows, encounter identifiers, or route specifications embedded in the question.
- Returning partial answers that do not reference actual FHIR data.
