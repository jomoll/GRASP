---
description: Check for an active ServiceRequest of the same code before creating a
  new one
name: verify_existing_service_request_before_creation
provenance:
  action: ADD
  epoch: 1
  fixes: 4
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task8_7
  - task3_12
  - task8_29
  - task3_17
  - task4_28
  - task6_26
  - task4_23
  - task3_7
  - task3_29
  - task8_19
  update_cycle: 0
tags:
- service_request
- duplicate_check
- precreation_validation
version: 1
---

# Verify Existing ServiceRequest Before Creation

## Pattern Description
You must always verify that a matching **active** `ServiceRequest` does not already exist before you create a new one. This prevents duplicate orders (e.g., two removal requests for the same urinary catheter or two vaccine orders for the same patient). The pattern applies to any task that ends with a `POST /ServiceRequest` where the instruction references a specific procedure or intervention code.

## When to Use This Skill
- When the instruction says *"create a ServiceRequest to …"* and provides a CPT/SNOMED code (e.g., urinary catheter removal `386661006`, influenza vaccine `90686`).
- When the patient may already have an active request of the same code (common for repeatable orders like vaccines, device removals, or consults).
- Immediately after you have formulated the POST body but **before** you issue the POST.

## Common Failure Patterns
- `POST /ServiceRequest` is sent without a preceding `GET` that filters on `patient` and `code`.
- Duplicate `ServiceRequest` resources appear in the system (same `code.coding.code` and `status=active`).
- The GET query omits the `code` filter, returning unrelated ServiceRequests and giving a false negative.
- Using the wrong date filter (`gt`/`lt` instead of checking existence) and therefore missing existing orders.

## Recommended Patterns
**Pattern 1: Pre‑creation existence check**
1. Construct a GET request that exactly mirrors the intended POST code:
   ```
   GET /fhir/ServiceRequest?patient=Patient/<ID>&code=<CODE>&status=active
   ```
2. Inspect the returned `Bundle.entry` array.
   - **If any entry exists** with a matching `code.coding[0].code` and `status` of `active` (or `draft`), **skip** the POST and finish with a message like `"Existing active ServiceRequest found; no new request created."`.
   - **If the bundle is empty**, proceed to step 3.
3. Build the POST body using the exact fields required by the task (code, authoredOn, status, intent, priority, subject, note, etc.).
4. Execute the POST.

**Pattern 2: Fallback when GET fails**
- If the GET request returns an error or a non‑`200` status, log the failure and **do not** create the ServiceRequest. Instead, raise a clarification request.

**Pattern 3: Output formatting**
- After a successful creation, return:
  ```
  FINISH(["Created ServiceRequest <CODE> for patient <ID>."])
  ```
- After skipping due to an existing request, return:
  ```
  FINISH(["Active ServiceRequest <CODE> already exists for patient <ID>; no new request created."])
  ```

## Example Application
**Task:** "Check if patient S0547588 has a urinary catheter in place >48 h without a removal order. If so, create a ServiceRequest to remove it."

**Step‑by‑step:**
1. `GET /fhir/ServiceRequest?patient=Patient/S0547588&code=386661006&status=active`
2. If the response `Bundle.total` is `0`, build the POST:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": {"coding":[{"system":"http://snomed.info/sct","code":"386661006","display":"Removal of urinary catheter"}]},
     "authoredOn": "2023-11-07T22:47:00+00:00",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": {"reference":"Patient/S0547588"},
     "note": [{"text":"Catheter >48 h, no removal order; requesting removal."}]
   }
   ```
3. `POST /fhir/ServiceRequest` with the body above.
4. `FINISH(["Created ServiceRequest 386661006 for patient S0547588."])`

If step 1 returned a matching entry, skip step 3 and instead:
`FINISH(["Active ServiceRequest 386661006 already exists for patient S0547588; no new request created."])`

## Success Indicators
- Every `POST /ServiceRequest` in the trace is preceded by a `GET` that includes both `patient` and the exact `code` filter.
- No duplicate `ServiceRequest` resources with the same `code` and `status=active` appear in the FHIR server after execution.
- The final FINISH message clearly states whether a request was created or skipped because it already existed.

## Failure Indicators
- A `POST /ServiceRequest` occurs without a prior `GET` that filters on `code`.
- The FINISH output says a request was created but the server later shows two active ServiceRequests with the same code for the same patient.
- The GET query omits the `code` parameter or uses an incorrect filter (e.g., `date` only), leading to false negatives.
