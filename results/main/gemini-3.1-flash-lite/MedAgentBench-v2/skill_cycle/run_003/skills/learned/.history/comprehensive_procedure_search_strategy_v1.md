---
description: Perform exhaustive searches for procedures by removing date filters when
  initial time-constrained searches return empty.
name: comprehensive_procedure_search_strategy
provenance:
  action: ADD
  epoch: 0
  fixes: 0
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task8_23
  - task9_8
  - task3_1
  - task1_11
  - task2_14
  - task9_14
  - task9_3
  - task9_9
  update_cycle: 0
tags:
- fhir
- search
- procedure
- false_negative
version: 1
---

# Comprehensive Procedure Search Strategy

## Pattern Description
When searching for historical procedures, applying a date filter (e.g., `date=ge...`) can lead to false negatives if the procedure exists but falls outside the specified window. To ensure accuracy, you must first attempt the search with the required date constraint. If that search returns no results, you must perform a secondary, broad search without the date filter to confirm the procedure's true absence before concluding it is missing.

## When to Use This Skill
- When a search for a specific procedure code (e.g., CPT, local code) with a date filter returns a `total: 0` bundle.
- When the task requires determining the "last" occurrence of a procedure and the initial date-restricted search yields no results.

## Common Failure Patterns
- Assuming a procedure does not exist because a date-restricted search returned empty.
- Failing to check for alternative codes or synonyms when the primary code search returns empty.
- Over-reliance on a single GET request with a date parameter.

## Recommended Patterns

**Pattern 1: Initial Search**
Issue the GET request with the patient ID, code, and the required date filter.

**Pattern 2: Verification Search**
If the initial search returns `total: 0`, issue a second GET request for the same patient and code(s) *without* the `date` parameter. 

**Pattern 3: Conclusion**
- If the second search returns results, identify the most recent one and compare its date to the threshold.
- If the second search also returns `total: 0`, only then conclude that the procedure has never been performed.

## Example Application

**Task:** "Determine the date of the last influenza vaccine (90686) for patient S0674240. If > 365 days ago, order a new one."

**Step-by-step:**
1. GET `.../Procedure?patient=S0674240&code=90686&date=ge2022-01-09` -> Returns `total: 0`.
2. GET `.../Procedure?patient=S0674240&code=90686` -> Returns `total: 0`.
3. Conclude no record exists and proceed to order.

## Success Indicators
- Agent performs a second, broader search when the first returns no results.
- Agent correctly identifies historical procedures that were missed by initial date-restricted queries.

## Failure Indicators
- Agent orders a duplicate procedure because it failed to find an existing one due to an overly restrictive date filter.
