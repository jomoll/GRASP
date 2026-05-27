---
description: Resolve external patient identifiers once and reuse the resolved FHIR
  Patient id/reference in all downstream reads and writes.
name: resolve_patient_identifier_before_dependent_search
provenance:
  action: MODIFY
  epoch: 0
  fixes: 5
  parent_version: 1
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task2_6
  - task10_17
  - task4_10
  - task3_16
  - task2_30
  - task3_27
  - task8_23
  - task3_1
  - task8_26
  - task10_16
  update_cycle: 1
tags:
- fhir
- patient-resolution
- search
- orders
version: 2
---

# Resolve Patient Identifier Before Dependent Search

## Pattern Description

When a task gives you an external patient identifier such as `S6538722`, you must first determine whether that token is the actual FHIR `Patient.id` or just a business identifier. After a successful `GET /Patient?identifier=...`, treat the returned Patient resource as the source of truth and carry its resolved `resource.id` forward into every dependent search and every write payload.

This skill changes behavior after patient lookup: instead of continuing to query `Observation`, `Procedure`, `MedicationRequest`, or posting new orders with the original external identifier, you must normalize to the resolved patient id/reference and use that same value consistently through the rest of the task.

## When to Use This Skill

- When the task names a patient with an MRN-like or external token such as `S6551923`
- When you plan any dependent search like `GET /Observation?patient=...`, `GET /Procedure?patient=...`, or `GET /MedicationRequest?patient=...`
- When you are about to create a resource with `subject.reference` or `patient.reference`
- When `GET /Patient?identifier=...` returns `Bundle.entry[0].resource.id` that may differ from the external identifier in the task
- When an initial downstream query using `patient=S...` returns large unrelated paginated bundles or empty results, suggesting the patient parameter is not normalized correctly

## Common Failure Patterns

- Querying `GET /Patient?identifier=S6538722` successfully, then still calling `GET /Procedure?patient=S6538722...`
- Mixing patient forms across requests: `patient=S6538722`, then `patient=Patient/S6538722`, then `patient=<uuid>` without anchoring to the resolved Patient resource
- Building POST bodies with `"subject":{"reference":"Patient/S6538722"}` when the Patient lookup returned a different `resource.id`
- Continuing with the raw external identifier after `Bundle.entry[0].resource.id` is available
- Assuming `fullUrl` or the task-supplied identifier is the canonical patient reference without checking `entry[0].resource.id`
- Abandoning the task after successful lookup/searches because the patient identity was never normalized into a stable variable for later steps

## Recommended Patterns

**Pattern 1: resolve once, then cache the canonical patient identity**
After `GET /Patient?identifier=<external_id>`, inspect:
- `Bundle.entry[0].resource.id`
- optionally `Bundle.entry[0].fullUrl`

Create and reuse these internal values:
- `resolved_patient_id = entry[0].resource.id`
- `resolved_patient_ref = "Patient/" + resolved_patient_id`

Use `resolved_patient_id` for search parameters unless the server clearly requires a reference form. Use `resolved_patient_ref` for POST bodies.

CORRECT: `GET /MedicationRequest?patient=8d23a6be-5f08-5d38-9f73-929fd2ab164f`
CORRECT: `"subject":{"reference":"Patient/8d23a6be-5f08-5d38-9f73-929fd2ab164f"}`
WRONG:   `GET /MedicationRequest?patient=S6550627`
WRONG:   `"subject":{"reference":"Patient/S6550627"}`

**Pattern 2: use the resolved id consistently in every downstream resource type**
Once resolved, all dependent queries must use the same patient identity:
- `Observation?patient=<resolved_patient_id>`
- `Procedure?patient=<resolved_patient_id>`
- `MedicationRequest?patient=<resolved_patient_id>`
- `ServiceRequest.subject.reference = Patient/<resolved_patient_id>`
- `MedicationRequest.subject.reference = Patient/<resolved_patient_id>`

If a query with `patient=<resolved_patient_id>` is unexpectedly empty, only then try `patient=Patient/<resolved_patient_id>` as a fallback. Do not revert to the original external identifier after you have a resolved Patient resource.

**Pattern 3: finish the task after using the normalized patient identity**
After downstream retrieval or POST succeeds, produce the requested conclusion with `FINISH(...)`. Do not keep paging or issuing alternate patient forms once you have enough information to answer. If you place an order, always follow the successful POST with a final statement that names the action taken.

## Example Application

**Task:** "Review COVID-19 vaccination status for patient S6538722. Find the most recent COVID-19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step-by-step:**

1. Resolve the patient:
   `GET /fhir/Patient?identifier=S6538722`
2. Read `Bundle.entry[0].resource.id`.
   Suppose it is `5f4d2b1c-1111-2222-3333-444455556666`.
3. Use that resolved id in downstream searches:
   `GET /fhir/Procedure?patient=5f4d2b1c-1111-2222-3333-444455556666&code=COVIDVACCINE&date=le2023-11-07T22:47:00Z`
4. If a booster is needed, create the order with the resolved reference:
   `POST /fhir/MedicationRequest`
   ```json
   {
     "resourceType": "MedicationRequest",
     "status": "active",
     "intent": "order",
     "subject": {"reference": "Patient/5f4d2b1c-1111-2222-3333-444455556666"},
     "medicationCodeableConcept": {
       "coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "91320"}],
       "text": "COVID-19 VAC booster"
     },
     "authoredOn": "2023-11-07T22:47:00Z"
   }
   ```
5. End with a final answer.

CORRECT output: `FINISH(["Most recent COVID-19 vaccine: none found.","COVID booster ordered today."])`
WRONG output:   `POST ... "subject":{"reference":"Patient/S6538722"}`
WRONG output:   stop after successful POST without calling `FINISH(...)`

## Success Indicators

- After a successful patient lookup, subsequent URLs use `patient=<resolved_patient_id>` or a deliberate fallback to `patient=Patient/<resolved_patient_id>`
- POST bodies use `subject.reference` or equivalent with `Patient/<resolved_patient_id>`
- The original external identifier is not reused in downstream patient fields once the real Patient id is known
- The task ends with a clear `FINISH(...)` after the retrieval or ordering work is complete

## Failure Indicators

- Any downstream request still uses `patient=S...` after `GET /Patient?identifier=S...` returned a Patient resource
- A POST body contains `Patient/S...` even though the resolved `resource.id` is different
- The agent oscillates between raw identifier, `Patient/S...`, and UUID without treating one resolved id as canonical
- The agent keeps paginating unrelated result sets or stops without a final answer because patient normalization was not maintained through the task
