---
description: Require a ServiceRequest POST whenever a task explicitly asks to order
  a referral, test, or procedure.
name: ensure_service_request_created_when_order_requested
provenance:
  action: ADD
  epoch: 2
  fixes: 6
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task8_14
  - task10_20
  - task2_6
  - task9_3
  - task10_8
  update_cycle: 0
tags:
- order
- servicerequest
- creation
version: 1
---

# Ensure ServiceRequest Created for Order Tasks

## Pattern Description
You must treat any instruction that explicitly asks to *order* a referral, medication, lab, imaging, or procedure as a mandatory ServiceRequest creation step. The pattern is reusable across all order‑type tasks: first verify the patient exists, then construct a valid `ServiceRequest` resource with the correct `code`, `subject`, `authoredOn`, `status`, `intent`, and any free‑text `note` required by the prompt. Skipping the POST or posting an incomplete resource is a failure.

## When to Use This Skill
- When the task description contains verbs like **order**, **request**, **create**, **place** followed by a clinical service (e.g., "order orthopedic surgery referral", "request HbA1c lab", "place medication order").
- When the task expects a side‑effect (resource creation) rather than a pure data answer.
- When the instruction includes required free‑text content (e.g., a note with Situation/Background/Assessment/Recommendation).

## Common Failure Patterns
- Agent only performs a `GET Patient` and then finishes without a `POST ServiceRequest`.
- `POST ServiceRequest` missing required fields (`code.coding.code`, `subject.reference`, `authoredOn`).
- Using the wrong resource type (e.g., `Observation` instead of `ServiceRequest`).
- Omitting the `note.text` when the prompt specifies exact wording.

## Recommended Patterns
**Pattern 1: Core order creation workflow**
1. **Identify the order intent** – parse the instruction for the service to be ordered and any required free‑text.
2. **GET the patient** – `GET {base}/Patient?identifier={MRN}`. Extract the patient reference (`Patient/{id}`).
3. **Build the ServiceRequest JSON**:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "<system>", "code": "<code>", "display": "<display>" }] },
     "authoredOn": "<current ISO datetime>",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/<id>" },
     "note": { "text": "<exact free‑text from prompt>" }
   }
   ```
   - Use the appropriate coding system (SNOMED, LOINC, etc.) as indicated in the prompt or a sensible default.
4. **POST the ServiceRequest** – `POST {base}/ServiceRequest` with the JSON body.
5. **Verify success** – if the POST response is accepted, proceed to `FINISH`.

**Pattern 2: Fallback if patient not found**
- If the patient GET returns `total: 0`, abort the order and `FINISH` with an error message like `"Patient not found; cannot create order."`.

**Pattern 3: Formatting the final answer**
- Do **not** include the created resource in the `FINISH` payload unless the task explicitly asks for confirmation. Usually `FINISH([])` or a short confirmation string is sufficient.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S2863714. Include the note: \"Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations.\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2863714`
2. Extract patient reference `Patient/S2863714`.
3. Construct ServiceRequest JSON with SNOMED code `306181000000106` and the exact note text.
4. `POST http://localhost:8080/fhir/ServiceRequest` with the JSON.
5. `FINISH([])`

**CORRECT output:**
```json
POST http://localhost:8080/fhir/ServiceRequest { ...valid JSON... }
FINISH([])
```
**WRONG output:**
- Missing POST, or POST with incomplete fields, or returning the note as part of the FINISH payload.

## Success Indicators
- The agent performs a `POST` to `/ServiceRequest` after the patient GET.
- The POST body contains all required fields and matches the free‑text note exactly.
- The final `FINISH` call occurs after a successful POST.

## Failure Indicators
- The agent finishes without a ServiceRequest POST.
- The POST body is missing `code.coding.code` or `subject.reference`.
- The note text differs from the instruction.
- The agent returns an empty list when the task required an order.
