---
description: "Ensures a non\u2011empty FINISH response confirming any FHIR order creation\
  \ (ServiceRequest, MedicationRequest, etc.)"
name: order_creation_confirmation
provenance:
  action: ADD
  epoch: 2
  fixes: 14
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task8_14
  - task10_20
  - task8_7
  - task8_29
  - task8_23
  - task8_13
  - task9_3
  - task10_21
  - task8_9
  - task8_21
  update_cycle: 0
tags:
- order
- confirmation
- FINISH
version: 1
---

# Order Creation Confirmation

## Pattern Description
You must always acknowledge a successful FHIR order creation with a concrete FINISH response. After you POST a `ServiceRequest`, `MedicationRequest`, `ProcedureRequest`, or any other order‑type resource, extract the returned resource identifier (or at least the resource type) and return a JSON array that confirms the creation. This prevents the agent from ending a task with an empty array, which the evaluation treats as a missing answer.

## When to Use This Skill
- When the user asks you to *order* something (e.g., "Order orthopedic surgery referral", "Create a medication order", "Schedule a lab test").
- After you have issued a `POST` request to a FHIR endpoint and received confirmation that the request was accepted (either via a `201 Created` response or a user message saying the request was executed successfully).
- The task does **not** require you to return clinical values; the only required output is a confirmation that the order exists.

## Common Failure Patterns
- `FINISH([])` – an empty array is returned after the POST.
- Returning the full posted JSON body inside `FINISH` instead of a concise confirmation.
- Forgetting to include the newly created resource’s identifier, making the answer ambiguous.
- Using a generic message that does not follow the expected array format (e.g., `FINISH("order created")`).

## Recommended Patterns
**Pattern 1: Primary confirmation strategy**
1. After the `POST` request, capture the response body (if the API returns the created resource) or note the user’s acknowledgement.
2. Extract `resourceType` and `id` fields:
   - `resourceType` → e.g., `ServiceRequest`
   - `id` → e.g., `12345`
3. Construct the FINISH payload as a **single‑element JSON array** containing a short confirmation string:
   ```
   FINISH(["ServiceRequest 12345 created"])   # if ID is known
   FINISH(["ServiceRequest created"])        # if ID is not available
   ```
4. Call `FINISH` **immediately** after the confirmation step; do not perform any further unrelated actions.

**Pattern 2: Fallback when no ID is returned**
- If the POST response body is empty and the user only says "POST request accepted", still produce a confirmation using the resource type you posted:
  ```
  FINISH(["ServiceRequest created"])   # minimal but non‑empty
  ```

**Pattern 3: Formatting rule**
- The FINISH array must contain **exactly one string element** for order‑creation tasks.
- Do **not** embed the full resource JSON, timestamps, or additional data inside the array.
- Ensure the string does not contain line breaks.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S3241217. Include the free‑text note as specified."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S3241217` – locate the patient.
2. `POST http://localhost:8080/fhir/ServiceRequest` with the referral payload.
3. Receive response (e.g., `{ "resourceType": "ServiceRequest", "id": "abcde123" , ... }`).
4. Extract `resourceType = "ServiceRequest"` and `id = "abcde123"`.
5. Call:
   ```
   FINISH(["ServiceRequest abcde123 created"])   # correct output
   ```
6. If the response body is empty but the user confirms success, call:
   ```
   FINISH(["ServiceRequest created"])
   ```

## Success Indicators
- The final agent output is `FINISH(["<ResourceType> <id> created"])` or `FINISH(["<ResourceType> created"])`.
- No empty array is emitted after an order‑creation task.
- The confirmation string matches the resource type you posted.

## Failure Indicators
- The agent ends with `FINISH([])` after a POST.
- The FINISH payload contains the full posted JSON or a non‑array value.
- The confirmation string is missing or malformed (e.g., contains extra whitespace or line breaks).
