---
description: Prevents duplicate ServiceRequest POSTs for the same code and patient
  within a single task
name: order_creation_deduplication
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task8_15
  - task8_26
  - task10_10
  - task10_12
  - task10_13
  - task8_5
  update_cycle: 1
tags: []
version: 1
---

# ServiceRequest Deduplication

## Pattern Description
You must ensure that the agent never creates two identical `ServiceRequest` resources for the same patient in the same task execution.  An "identical" request is defined by the combination of:
- `code.coding[0].system` and `code.coding[0].code` (the ordered service or lab)
- `subject.reference` (the patient MRN)
- `intent` and `status` (e.g., `order`/`active`)

Duplicate orders waste resources, can confuse downstream systems, and are a common source of the *unnecessary_service_request_created* failure mode.

## When to Use This Skill
- When the task description includes language such as *"order"*, *"create a referral"*, or *"request a lab"* and the agent is about to issue a `POST /ServiceRequest`.
- Immediately after a successful `POST /ServiceRequest` within the same task, before issuing any further `POST /ServiceRequest` for the same patient.
- When the agent has already performed a `GET /ServiceRequest` (or has cached the response) that shows an existing request matching the criteria.

## Common Failure Patterns
- Two consecutive `POST /ServiceRequest` calls with identical payloads (as seen in task8_5).
- A `POST /ServiceRequest` issued after a previous successful POST, but the agent does not remember the earlier request.
- Duplicate orders created because the agent re‑evaluates the same condition in a loop without tracking prior actions.

## Recommended Patterns
**Pattern 1: In‑memory deduplication before POST**
1. Maintain a temporary list `posted_requests` in the task context.
2. Before constructing a `ServiceRequest` payload, extract the three key identifiers:
   - `order_code = payload["code"]["coding"][0]["code"]`
   - `order_system = payload["code"]["coding"][0]["system"]`
   - `patient_ref = payload["subject"]["reference"]`
3. Search `posted_requests` for a record where all three fields match **and** `intent`/`status` are the same.
4. If a match is found, **skip** the `POST` and proceed directly to `FINISH` (or to the next step).
5. If no match, execute the `POST` and append the tuple `(order_system, order_code, patient_ref, intent, status)` to `posted_requests`.

**Pattern 2: Server‑side verification fallback**
1. After a successful `POST`, optionally perform a `GET /ServiceRequest?patient={patient}&code={code}` to confirm the request exists.
2. If the GET returns a resource that matches the just‑posted payload, treat it as confirmation and add it to `posted_requests`.
3. If the GET returns nothing, treat the POST as failed and retry or report an error.

**Pattern 3: Output formatting**
- When you skip a duplicate, the final `FINISH` should still report the original creation, e.g. `FINISH(["ServiceRequest created"])`.
- Do **not** output an empty array or a placeholder like `FINISH([])` when a duplicate was suppressed.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S6550627. ..."

**Step‑by‑step:**
1. Build the ServiceRequest payload (code `306181000000106`, patient `Patient/S6550627`).
2. Check `posted_requests` – it is empty, so proceed.
3. `POST http://localhost:8080/fhir/ServiceRequest` with the payload.
4. On success, append `("http://snomed.info/sct", "306181000000106", "Patient/S6550627", "order", "active")` to `posted_requests`.
5. Later in the same task, the agent attempts the same POST again.
6. The deduplication check finds the tuple already present → **skip** the POST.
7. Continue to `FINISH(["ServiceRequest created"])`.

**CORRECT output:** `FINISH(["ServiceRequest created"])`
**WRONG output:** two separate `POST` calls followed by `FINISH(["ServiceRequest created"])` (duplicate order).

## Success Indicators
- Exactly one `POST /ServiceRequest` is observed for a given `(code, patient)` pair per task.
- The `FINISH` response reports creation once, even if the agent evaluated the ordering condition multiple times.
- No warning logs about "ServiceRequest POST accepted but resource not found" due to duplicate overwrites.

## Failure Indicators
- Multiple `POST /ServiceRequest` calls with identical payloads appear in the trace.
- The `FINISH` output is produced after the second POST, indicating the duplicate was not suppressed.
- The system note shows a warning about duplicate resources or missing retrieval after POST.
