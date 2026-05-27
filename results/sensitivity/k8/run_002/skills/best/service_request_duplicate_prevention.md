---
description: Prevent duplicate ServiceRequest POSTs by checking for existing active
  requests first
name: service_request_duplicate_prevention
provenance:
  action: MODIFY
  epoch: 3
  fixes: 9
  parent_version: 1
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - task5_7
  - task9_11
  - task5_19
  - task9_9
  - task8_19
  - task9_1
  - task9_22
  - task5_16
  - task5_17
  update_cycle: 0
tags:
- duplicate-prevention
- service-request
version: 2
---

# Service Request Duplicate Prevention

## Pattern Description
You must ensure that the system never creates two identical active `ServiceRequest` resources for the same patient. Before issuing any `POST /ServiceRequest`, first verify that no active request with the same `code` already exists for that patient. This prevents redundant orders and keeps the chart clean.

## When to Use This Skill
- **When the agent is about to POST a `ServiceRequest`** (e.g., ordering a referral, lab, or procedure).
- The request targets a specific patient (`subject.reference = "Patient/<MRN>"`).
- The `code.coding[0].system` and `code.coding[0].code` uniquely identify the service being ordered.
- The desired `status` of the new request would be `active` (or any status that signifies an open order).

## Common Failure Patterns
- The agent posts a `ServiceRequest` without first searching for existing active requests.
- The agent performs a `GET /ServiceRequest` but ignores a non‑zero `Bundle.total` and still posts.
- The duplicate check only looks at a subset of fields (e.g., ignores `code.display` or `status`).

## Recommended Patterns
**Pattern 1: Pre‑flight duplicate check**
1. **Construct the GET URL** using the exact patient reference and the full coding system+code of the request:
   ```
   GET {base}/ServiceRequest?patient=Patient/<MRN>&code={system}|{code}&status=active
   ```
2. **Inspect the response Bundle**:
   - If `total > 0`, an active request already exists → **skip the POST** and finish with a message like `FINISH(["ServiceRequest already exists"])`.
   - If `total == 0`, proceed to step 3.
3. **POST the new ServiceRequest** exactly as specified.

**Pattern 2: Fallback safety net**
- If the GET fails (network error or non‑200), **do not assume safety**; abort the operation and report the error rather than risking a duplicate.

**Pattern 3: Consistent response handling**
- Always treat the `code` as a combination of `system` and `code`. Do **not** rely on `display` text because it may vary.
- Ensure the `status` filter is present; otherwise a completed request could be mistaken for an active one.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S6530813."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/ServiceRequest?patient=Patient/S6530813&code=http://snomed.info/sct|306181000000106&status=active`
2. Response shows `total: 0` → no active referral exists.
3. `POST http://localhost:8080/fhir/ServiceRequest` with the referral payload.
4. `FINISH(["Referral ordered"])`

**If the GET had returned `total: 1`** (an existing active referral), the agent would skip step 3 and instead `FINISH(["Referral already exists"])`.

## Success Indicators
- No second `POST /ServiceRequest` is issued when a prior active request is found.
- The agent logs a clear “already exists” message and calls `FINISH` without posting.
- All duplicate‑prevention tests pass with `total > 0` cases blocked.

## Failure Indicators
- Two `POST /ServiceRequest` calls with identical patient and code appear in the trace.
- The agent performs a GET but still proceeds to POST despite `total > 0`.
- The GET URL omits the `status=active` filter, allowing completed requests to be ignored.
