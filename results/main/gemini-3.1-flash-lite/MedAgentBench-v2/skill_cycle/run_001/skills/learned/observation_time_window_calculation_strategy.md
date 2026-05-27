---
description: Ensures accurate time-based filtering and weighted average calculation
  for longitudinal observation data.
name: observation_time_window_calculation_strategy
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task3_29
  - task2_1
  - task4_27
  - task3_3
  - task3_7
  - task2_14
  - task3_27
  - task2_30
  - task3_16
  - task9_1
  update_cycle: 1
tags:
- observation
- time-window
- calculation
version: 1
---

# Observation Time Window Calculation Strategy

## Pattern Description
When calculating metrics over specific time windows (e.g., 6 or 12 hours), you must first retrieve all relevant observations without restrictive date filters to ensure the full dataset is available. Once retrieved, you must manually filter the observations based on the `effectiveDateTime` field relative to the current time. If multiple observations exist, calculate the average using all values within the window, rather than relying on a single or arbitrary record.

## When to Use This Skill
- When a task requires calculating an average, trend, or status over a specific lookback period (e.g., "past 6 hours").
- When initial searches return no results, but you suspect historical data exists outside a narrow query.
- When multiple observations are present and a simple average of all valid data points is required.

## Common Failure Patterns
- Relying on the server to filter by date in the initial GET request, which often misses records if the date format is slightly off or the server index is incomplete.
- Selecting only the most recent record instead of averaging all records within the specified window.
- Failing to account for the current time context provided in the task description when calculating the window boundaries.

## Recommended Patterns

**Pattern 1: Broad Retrieval**
Always perform an initial search for the observation category or code without date parameters to ensure you capture the full history.

**Pattern 2: Local Filtering**
After receiving the bundle, iterate through the `entry` list. For each `Observation`, parse the `effectiveDateTime`. Compare this timestamp against the calculated start time (e.g., `current_time - 6 hours`).

**Pattern 3: Calculation**
Collect all `valueQuantity.value` fields for observations where the `effectiveDateTime` falls within the window. Calculate the arithmetic mean: `sum(values) / count(values)`.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours."

**Step-by-step:**
1. GET `.../Observation?patient=S123&code=HEARTRATE` (no date filter).
2. Filter the returned list: keep only observations where `effectiveDateTime` >= `2023-11-07T16:47:00`.
3. Extract `valueQuantity.value` for all kept observations.
4. If 3 values are found (e.g., 80, 84, 76), calculate `(80+84+76)/3 = 80`.
5. FINISH(["The average heart rate is 80 bpm."])

## Success Indicators
- Agent performs a broad search first.
- Agent explicitly calculates the mean of multiple values found within the window.

## Failure Indicators
- Agent returns "no records found" despite data being present in the bundle.
- Agent uses only the single most recent value instead of an average.
