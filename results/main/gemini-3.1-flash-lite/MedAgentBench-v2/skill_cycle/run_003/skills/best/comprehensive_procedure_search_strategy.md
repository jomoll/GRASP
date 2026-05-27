---
description: Expand search to include status verification, device/observation checks,
  and broader code lookups for procedures.
name: comprehensive_procedure_search_strategy
provenance:
  action: MODIFY
  epoch: 3
  fixes: 6
  parent_version: 2
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - task3_30
  - task1_26
  - task3_10
  - task3_27
  - task4_23
  - task4_21
  - task8_19
  - task4_27
  - task2_9
  - task2_14
  update_cycle: 1
tags:
- procedure
- search
- status-verification
version: 3
---

## Skill Title
Comprehensive Procedure and Status Verification Strategy

## Pattern Description
When searching for a procedure or an active clinical state (like an indwelling catheter), do not rely solely on a single code or resource type. Procedures may be recorded in `Procedure`, `ServiceRequest`, or `Immunization` resources. Furthermore, an active state often requires checking the `status` field (e.g., 'in-progress', 'active') and, for devices, checking `Observation` or `Device` resources if the procedure record is missing or stale.

## When to Use This Skill
- When a search for a procedure by code returns no results or stale results.
- When checking for the duration of an active state (e.g., indwelling catheter > 48 hours).
- When the task requires verifying if a procedure is 'active' or 'completed'.

## Common Failure Patterns
- Searching only `Procedure` and ignoring `ServiceRequest` or `Immunization`.
- Failing to check the `status` field, leading to the inclusion of 'completed' or 'entered-in-error' records as active.
- Assuming a procedure code is the only way to identify a state; missing `Observation` resources that track device duration.
- Failing to handle future-dated records or discrepancies between current time and procedure `performedDateTime`.

## Recommended Patterns

**Pattern 1: Multi-Resource Search**
If a search for a specific code in `Procedure` returns empty, perform a broader search on `Procedure`, `ServiceRequest`, and `Immunization` for the patient without the code filter to inspect the full history.

**Pattern 2: Status and Time Filtering**
Always inspect the `status` field. For active states, filter for `status=active` or `status=in-progress`. If checking duration, compare the `performedDateTime` or `authoredOn` against the current task time. If the date is in the future, flag it as a potential data discrepancy.

**Pattern 3: Device/Observation Fallback**
If the procedure code search fails for a device-based task (like a catheter), search `Observation` resources with `category=vital-signs` or `category=procedure` to find evidence of the device's presence.

## Example Application
**Task:** "Check if patient has a urinary catheter in place > 48 hours."
1. GET `Procedure?patient=ID&code=NUR1373`
2. If empty, GET `Procedure?patient=ID` and `ServiceRequest?patient=ID` to scan all records.
3. Check `status` of found records. If `status` is 'completed', the catheter is not active.
4. If no `Procedure` found, GET `Observation?patient=ID&category=vital-signs` to see if the catheter is documented there.

## Success Indicators
- Agent identifies the correct procedure even when the primary code search returns zero results.
- Agent correctly ignores 'completed' procedures when looking for active states.

## Failure Indicators
- Agent reports 'no procedure found' when a record exists under a different resource type or status.
