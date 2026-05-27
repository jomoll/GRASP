---
description: Expand search to include Immunization and ServiceRequest resources when
  procedure history is incomplete, with explicit guard clauses to prevent premature
  or duplicate actions.
name: comprehensive_procedure_search_strategy
provenance:
  action: MODIFY
  epoch: 0
  fixes: 3
  parent_version: 1
  probe_score: 2
  regressions: 3
  triggering_sample_ids:
  - task1_10
  - task3_27
  - task3_16
  - task4_27
  - task1_20
  - task9_6
  - task9_28
  - task6_26
  - task3_3
  - task2_22
  update_cycle: 1
tags:
- FHIR
- SearchStrategy
- ClinicalDecisionSupport
version: 2
---

# Comprehensive Procedure and Order Search Strategy

## Pattern Description
When a task requires verifying the history or status of a clinical intervention, a single search on the `Procedure` resource is often insufficient. Clinical data is distributed across `Procedure`, `Immunization`, and `ServiceRequest`. If an initial search returns no results, perform an exhaustive search across all relevant resource types before concluding that an action is required.

## When to Use This Skill
- When a task asks to find the "most recent" instance of a procedure or vaccine.
- When a task requires checking if a procedure or order has been performed or is currently active.
- When an initial search for a procedure returns zero results, but the task implies a history might exist.

## Guard Clauses (Preventing Regressions)
- **Temporal Validation:** Before creating a new order, verify that the time elapsed since the last procedure actually meets the criteria specified in the prompt (e.g., > 48 hours or > 12 months). Do not assume an action is required simply because a record is old or missing.
- **Resource Integrity:** When checking for existing orders, ensure the search covers both `Procedure` (completed) and `ServiceRequest` (pending/active) to avoid duplicate orders.
- **Negative Result Confirmation:** If a search returns zero results, explicitly state that no records were found across all checked resources before proceeding to create a new order.

## Recommended Patterns

**Pattern 1: Multi-Resource Search**
If the primary search (e.g., `Procedure`) returns no results, query other relevant resources. For vaccines, check `Immunization`. For orders or pending procedures, check `ServiceRequest`.

**Pattern 2: Unfiltered Fallback**
If a date-filtered search returns no results, perform a second search without the date filter to confirm the patient has no history of the intervention at all.

**Pattern 3: Verification of Existing Orders**
Before creating a new `ServiceRequest`, search `ServiceRequest` for the patient to ensure an active or pending order for the same indication does not already exist.

## Success Indicators
- Agent performs multiple searches across `Procedure`, `Immunization`, and `ServiceRequest` when initial results are empty.
- Agent calculates time intervals (e.g., 48 hours, 12 months) against the current time before deciding to act.

## Failure Indicators
- Agent creates a duplicate order because it failed to check `ServiceRequest`.
- Agent acts on a procedure that does not meet the temporal criteria (e.g., ordering removal for a catheter in place < 48 hours).
