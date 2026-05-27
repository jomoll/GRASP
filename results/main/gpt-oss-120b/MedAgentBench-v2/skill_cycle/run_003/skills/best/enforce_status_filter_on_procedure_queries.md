---
description: Require a status filter (e.g., status=active) on Procedure searches that
  determine current patient conditions
name: enforce_status_filter_on_procedure_queries
provenance:
  action: ADD
  epoch: 1
  fixes: 2
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task3_19
  - task1_13
  - task3_30
  - task8_23
  - task2_26
  - task4_21
  - task2_15
  - task3_16
  - task1_20
  - task8_5
  update_cycle: 1
tags:
- procedure
- status-filter
- clinical-decision
version: 1
---

# Enforce Status Filter on Procedure Queries

## Pattern Description
You must always include a `status` search parameter when querying the `Procedure` resource to determine whether a condition or device is currently in place. The default FHIR search returns all procedures regardless of completion, which can cause false‑positive decisions (e.g., assuming a urinary catheter is still present when the only record is a completed removal). By explicitly filtering for `status=active` (or another appropriate status such as `in-progress`), you ensure the query reflects the present state of the patient.

## When to Use This Skill
- When the instruction asks to *check if a device/procedure is still in place* (e.g., urinary catheter, central line, wound dressing).
- When the decision to create a ServiceRequest, MedicationRequest, or other order depends on the *current* existence of a Procedure.
- Any `GET /Procedure` that will be used for a conditional creation or cancellation of a resource.

## Common Failure Patterns
- Omitting `status` entirely, causing the query to return historic procedures that are no longer relevant.
- Using only a date filter (`date=le…`) without a status filter, leading to inclusion of completed or cancelled procedures.
- Assuming that the absence of a `status` filter implies “active only”.

## Recommended Patterns
**Pattern 1: Core status‑filter rule**
1. Identify the purpose of the Procedure query (e.g., “is a urinary catheter still present?”).
2. Add `status=active` (or `status=in-progress` if appropriate) to the query string.
3. Keep any additional date filters **in addition** to the status filter.

```text
CORRECT: GET /Procedure?patient=XYZ&code=NUR1373&status=active&date=le2023-11-05T22:47:00Z
WRONG:   GET /Procedure?patient=XYZ&code=NUR1373&date=le2023-11-05T22:47:00Z   (no status)
```

**Pattern 2: Fallback verification**
- If the response `total` is 0, double‑check that the query included a status filter; if not, re‑issue the request with `status=active` before concluding the condition is absent.

**Pattern 3: Output formatting**
- When reporting the result, explicitly state whether an *active* procedure was found.

## Example Application
**Task:** "Check if patient S3241217 has a urinary catheter that has been in place for more than 48 hours without a documented removal order. If so, create a ServiceRequest to remove the catheter."

**Step‑by‑step:**
1. Issue GET with status filter:
   ```
   GET http://localhost:8080/fhir/Procedure?patient=S3241217&code=NUR1373&status=active&date=le2023-11-05T22:47:00Z
   ```
2. Inspect `total` in the Bundle response.
   - If `total > 0`, the catheter is still present → proceed to create ServiceRequest.
   - If `total == 0`, conclude no active catheter; FINISH with a negative statement.
3. Construct ServiceRequest only after confirming an active procedure.

**CORRECT output:** `FINISH(["Created ServiceRequest to remove urinary catheter for patient S3241217."])`
**WRONG output:** `FINISH(["Created ServiceRequest …"])` when the initial query lacked a status filter and returned a historic placement.

## Success Indicators
- Every Procedure GET used for a presence check includes `status=active` (or appropriate status).
- The agent never creates a removal order based solely on a historic procedure without a status filter.
- Log messages (if any) mention “status filter applied”.

## Failure Indicators
- Procedure queries missing `status=` when the task involves current condition assessment.
- ServiceRequests are created after a Procedure query that returned only completed records.
- Agent reports “no status filter” in system notes or warnings.
