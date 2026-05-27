---
description: Ensures historical records are captured by performing an initial broad
  search before applying restrictive date filters.
name: fhir_search_temporal_fallback_strategy
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task8_26
  - task8_23
  - task8_29
  - task1_13
  - task3_10
  - task3_16
  - task2_14
  - task2_6
  - task8_5
  - task4_21
  update_cycle: 1
tags:
- fhir
- search
- temporal-logic
version: 1
---

## Skill Title
FHIR Search Temporal Fallback Strategy

## Pattern Description
When searching for historical procedures or observations to determine if a recent event occurred, agents often apply a restrictive date filter (e.g., `date=ge[date]`) too early. If the initial search returns no results, the agent may incorrectly conclude that no such event exists. This skill mandates a two-step search pattern: first, perform a broad search to confirm the existence of any historical records, and second, apply temporal logic to the retrieved data.

## When to Use This Skill
- When a task requires checking for the existence of a procedure or observation within a specific timeframe (e.g., "within the last 12 months").
- When an initial search with a date filter returns zero results, but the task requires verifying if an event occurred at any point in the past.

## Common Failure Patterns
- Applying a `date=ge[date]` filter in the first GET request, causing the agent to miss older records that might be relevant for context or to confirm the absence of a procedure.
- Assuming that a zero-result search with a date filter is definitive proof that no such procedure has ever occurred.

## Recommended Patterns

**Pattern 1: Broad Initial Search**
If you need to check for a procedure or observation, start by searching without a date filter to see if any records exist for the patient.

**Pattern 2: Temporal Filtering**
Once you have the full list of records, filter them locally based on the required date range. If the list is empty, you can confidently conclude no such event occurred.

**Pattern 3: Verification**
If the broad search returns results, inspect the `effectiveDateTime` or `performedDateTime` fields to determine if the most recent event falls within the required window.

## Example Application

**Task:** "Find the date of the most recent CT Abdomen procedure. If performed more than 12 months ago, order a new one."

**Step-by-step:**
1. Issue GET `.../Procedure?patient=S123&code=IMGCT0491` (no date filter).
2. If the bundle is empty, conclude no procedure exists and proceed to order.
3. If the bundle contains entries, extract the dates from the resources.
4. Compare the most recent date to the current date to decide if an order is needed.

CORRECT output: `GET .../Procedure?patient=S123&code=IMGCT0491`
WRONG output: `GET .../Procedure?patient=S123&code=IMGCT0491&date=ge2022-11-07` (if this is the only search performed).

## Success Indicators
- The agent retrieves historical records that were previously missed due to restrictive date filters.
- The agent correctly identifies the most recent procedure date even if it is older than the initial filter threshold.

## Failure Indicators
- The agent continues to use restrictive date filters in the first request, leading to false negatives.
