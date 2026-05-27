---
description: "Enforce inclusion of status=active on MedicationRequest searches before\
  \ any order\u2011creation logic."
name: medicationrequest_status_filter_enforcement
provenance:
  action: ADD
  epoch: 1
  fixes: 0
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task2_30
  - task8_19
  - task3_14
  - task2_22
  - task2_14
  - task3_7
  - task8_7
  - task1_20
  - task4_11
  - task3_27
  update_cycle: 1
tags:
- medicationrequest
- status-filter
- active-order-enforcement
version: 1
---

# MedicationRequest Status Filter Enforcement

## Pattern Description
You must always restrict a GET request for `MedicationRequest` resources to active orders before you decide whether to create, discontinue, or leave orders unchanged.  By requiring the query parameter `status=active` (or an equivalent FHIR search on the `status` element), the agent avoids false assumptions that a patient has no active DVT prophylaxis, opioid, or other medication when the server simply returned inactive or cancelled records.  This guard is reusable for any workflow that inspects a patient's medication list and makes decisions based on the count or properties of *active* orders.

## When to Use This Skill
- When a task instructs you to **verify**, **create**, **discontinue**, or **modify** a medication order (e.g., DVT prophylaxis, opioid‑naloxone pairing, COVID‑19 booster eligibility).
- The agent is about to issue a `GET /MedicationRequest` without an explicit `status=` filter.
- The decision logic depends on the number of *active* orders (e.g., "exactly one active DVT prophylaxis order").

## Common Failure Patterns
- `GET /MedicationRequest?patient=XYZ` – missing `status` filter, leading to inclusion of `inactive`, `cancelled`, or `stopped` entries.
- Assuming zero active orders because the returned bundle is empty, when the server omitted inactive records.
- Creating a duplicate order because the existing active order was hidden by a filter that excluded `status=active`.
- Discontinuing the wrong order when the bundle contains a mix of statuses and the agent does not check the `status` field.

## Recommended Patterns
**Pattern 1: Core enforcement rule**
1. Before issuing any `GET /MedicationRequest` for a patient, check the URL.
2. If the query string does **not** contain `status=active` (case‑insensitive), **modify** the request to append `&status=active`.
3. Issue the corrected request and store the response.
4. Proceed with order‑logic **only** on entries where `resource.status == "active"`.

```json
CORRECT URL: http://localhost:8080/fhir/MedicationRequest?patient=S12345&status=active
WRONG URL: http://localhost:8080/fhir/MedicationRequest?patient=S12345
```

**Pattern 2: Fallback verification**
- If the task explicitly supplies a `status` filter that is *not* `active` (e.g., `status=completed`), abort the task and raise a warning: "Task requires active orders; received status=completed."
- If the server returns a bundle with `total > 0` but none of the entries have `status == "active"`, treat the result as **no active orders** and continue with creation logic.

**Pattern 3: Output formatting rule**
- When reporting the count of active orders, output a plain integer inside `FINISH([count])`.
- Do **not** embed status text or full resource JSON in the final answer.

## Example Application
**Task:** "Verify that patient S6227720 has exactly one active DVT prophylaxis order. If there are zero orders, create one. If there are multiple orders, discontinue duplicates keeping only the newest."

**Step‑by‑step:**
1. Build the GET URL: `http://localhost:8080/fhir/MedicationRequest?patient=S6227720&status=active`.
2. Issue the request and receive a Bundle.
3. Count entries where `resource.status == "active"`.
   - If count == 1 → `FINISH([1])`.
   - If count == 0 → POST a new `MedicationRequest` with `status: "active"`.
   - If count > 1 → Identify the newest by `authoredOn`, POST a `MedicationRequest` with `status: "cancelled"` (or `inactive`) for all but the newest, then `FINISH([1])`.

**CORRECT output:** `FINISH([1])`
**WRONG output:** `FINISH(["Task completed: one active order present."])`

## Success Indicators
- Every `GET /MedicationRequest` URL in the trace contains `status=active`.
- The agent never creates a duplicate active order when an active one already exists.
- FINISH calls contain a numeric count of active orders, not a free‑text message.

## Failure Indicators
- GET URLs missing the `status` parameter.
- The agent reports success based on a bundle that includes inactive or cancelled orders.
- Duplicate active orders are created because the existing active order was not seen.
- FINISH output includes explanatory text instead of a plain numeric array.
