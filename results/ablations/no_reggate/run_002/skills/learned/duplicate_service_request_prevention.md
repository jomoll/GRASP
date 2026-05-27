---
description: Prevents creating duplicate ServiceRequest resources for the same patient
  and code within a single task.
name: duplicate_service_request_prevention
provenance:
  action: ADD
  epoch: 1
  fixes: 12
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task10_24
  - task5_17
  - task9_6
  - task8_29
  - task5_7
  - task9_27
  - task9_14
  - task9_20
  - task10_12
  update_cycle: 0
tags:
- order
- duplicate
- service_request
version: 1
---

# Duplicate ServiceRequest Prevention

## Pattern Description
You must ensure that a ServiceRequest (order, referral, lab test, etc.) is created at most once per patient for a given clinical purpose during a single task execution. Before issuing a POST for a ServiceRequest, verify that an equivalent request does not already exist either in the current session (already posted) or in the FHIR server. This avoids unnecessary duplicate orders, reduces clinician workload, and prevents resource‑creation errors.

## When to Use This Skill
- When the user instruction explicitly asks to *order* or *refer* a service (e.g., "order a new HbA1c test", "place an orthopedic surgery referral").
- The task may involve conditional logic that could cause the same POST to be executed more than once (e.g., after a GET, after a verification step, or in a loop).
- The same patient identifier and the same `code.coding[0].code` (or `code.text` when coding is absent) are used for the ServiceRequest.

## Common Failure Patterns
- Two consecutive `POST /ServiceRequest` calls with identical `subject.reference` and `code.coding[0].code`.
- A POST is issued before confirming that the patient exists, leading to a duplicate attempt after the GET resolves the patient.
- The agent posts a ServiceRequest, receives a success note, but later repeats the POST because it did not record that the request was already sent.

## Recommended Patterns
**Pattern 1: Pre‑POST existence check**
1. **Construct a search URL** to look for existing ServiceRequests:
   ```
   GET {base}/ServiceRequest?patient={patientId}&code={code}
   ```
   - `patientId` is the patient MRN (e.g., `S6307599`).
   - `code` is the LOINC or SNOMED code used in the request (e.g., `4548-4` for HbA1c, `306181000000106` for orthopedic referral).
2. **Inspect the Bundle response**:
   - If `total > 0` and any entry has `status` of `active` or `completed`, **skip the POST** and note that the request already exists.
   - If `total == 0`, proceed to step 3.

**Pattern 2: In‑session duplicate guard**
1. Maintain an in‑memory set `created_requests` keyed by `<patientId>|<code>` for the duration of the task.
2. Before any POST, check if the key is present:
   - If present, **do not POST** again.
   - If absent, add the key to the set **after a successful POST**.

**Pattern 3: Post‑creation verification**
1. After a POST, wait for the system verification note.
2. If verification indicates the resource was not stored (e.g., "resource not found on retrieval"), **retry** only if the in‑session guard does not already contain the key.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S6307599. ..."

**Step‑by‑step:**
1. `GET /Patient?identifier=S6307599` – confirm patient exists.
2. Build search URL: `GET /ServiceRequest?patient=S6307599&code=306181000000106`.
3. Receive Bundle with `total=0` → no existing referral.
4. Check `created_requests` – key not present.
5. `POST /ServiceRequest` with the referral payload.
6. Receive verification note → add key `S6307599|306181000000106` to `created_requests`.
7. Continue task; any later attempt to create the same referral will be blocked.

**CORRECT output:**
```json
FINISH(["Referral placed for patient S6307599"])
```
**WRONG output (duplicate):**
```json
POST /ServiceRequest {...}
POST /ServiceRequest {...}   // second identical POST
FINISH(["Referral placed"])
```

## Success Indicators
- Exactly one `POST /ServiceRequest` is issued for a given patient‑code pair per task.
- The agent logs (or comments) that an existing request was found when a duplicate is avoided.
- No system warnings about duplicate resources.

## Failure Indicators
- Two or more POSTs with identical patient and code appear in the trace.
- The agent proceeds to POST without performing the pre‑POST GET search.
- The in‑session guard is not updated after a successful POST, leading to repeated attempts.
