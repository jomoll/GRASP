---
description: Enforce strict time-based filtering for lab results, ensuring search
  results are validated against the current system time before concluding no data
  exists.
name: temporal_observation_filtering
provenance:
  action: ADD
  epoch: 2
  fixes: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task10_13
  - task9_9
  - task5_19
  - task2_17
  - task4_26
  - task5_3
  - task9_27
  - task10_12
  - task10_18
  - task2_26
  update_cycle: 1
tags:
- FHIR
- temporal-logic
- data-validation
version: 1
---

## Temporal Observation Filtering

When a task requires checking for a lab result within a specific timeframe, you must explicitly compare the `effectiveDateTime` or `issued` field of the retrieved Observation against the current system time provided in the task context.

## When to Use This Skill

- When a task specifies a time-bound condition for a lab result (e.g., "within 24 hours", "within 1 year").
- When you need to decide whether to order a new test based on the age of the most recent result.

## Critical Guard Clause: Handling Empty Search Results

If a FHIR search returns a `total: 0` or an empty bundle, do not assume the data is missing without verifying the search parameters. However, if the search is correctly formed and returns no results, you must conclude that no measurement is available (e.g., return -1) rather than assuming a hidden record exists. 

**Crucially**, do not use this filtering logic to discard valid search results that are within the window. Ensure that if a search returns results, you parse the timestamps of *all* returned entries before deciding if a valid record exists.

## Recommended Patterns

**Pattern 1: Timestamp Validation**
1. Retrieve the list of Observations.
2. If the bundle is empty, return the "not found" value (e.g., -1).
3. For each entry, extract the `effectiveDateTime`.
4. Calculate the difference between the current time and the `effectiveDateTime`.
5. Filter out any observations where the difference exceeds the task's time limit.

**Pattern 2: Decision Logic**
- If no observations remain after filtering, treat the result as "not found".
- If multiple observations remain, select the one with the most recent `effectiveDateTime`.

## Example Application

**Task:** "Check patient S123's last HbA1C within 1 year."

**Step-by-step:**
1. GET `Observation?code=4548-4&patient=S123`.
2. If the bundle is empty, report "not found".
3. If results exist, parse `effectiveDateTime` for all entries.
4. Compare each date to the current date. If the most recent valid result is > 1 year old, report "not found".
