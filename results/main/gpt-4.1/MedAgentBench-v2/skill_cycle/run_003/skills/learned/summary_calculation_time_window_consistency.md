---
description: Ensure consistent and correct time window queries for all summary calculations
  (e.g., averages over 6h and 12h).
name: summary_calculation_time_window_consistency
provenance:
  action: ADD
  epoch: 4
  fixes: 6
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task6_26
  - task8_29
  - task9_8
  - task3_16
  - task2_30
  - task8_26
  - task3_30
  - task3_17
  - task2_15
  - task4_10
  update_cycle: 1
tags:
- summary
- time window
- observation
- query
- average
- calculation
- consistency
version: 1
---

# Summary Calculation Time Window Consistency

## Pattern Description

When calculating summary statistics (such as averages, minimums, or maximums) over multiple time windows (e.g., past 6 hours and past 12 hours), you must ensure that each window is queried using the correct and consistent time boundaries. This means that for each requested window, you should issue a FHIR search that covers exactly the intended interval, and not use mismatched or inconsistent start times. This is especially important when the task requests multiple windows in a single instruction, as inconsistent queries can lead to missing or incorrect data for one or more windows.

This skill is critical for tasks that require reporting or comparing values across different time intervals, such as "average heart rate over the past 6 hours and the past 12 hours." Failing to align the query windows can result in missing data, incorrect calculations, or inconsistent use of default values (e.g., 'N/A').

## When to Use This Skill

- When a task requests summary statistics (average, min, max, etc.) over multiple time windows for the same measurement.
- When constructing multiple FHIR Observation queries for the same code but different time intervals in a single task.
- When the output must report a value for each requested window, even if some windows have no data.

## Common Failure Patterns

- Using inconsistent or incorrect start times for each time window (e.g., using the wrong date parameter for the 12-hour window).
- Querying the same time window twice instead of two distinct windows.
- Returning 'N/A' for a window that actually has data because the query window was too narrow or misaligned.
- Overlapping or non-nested queries that do not match the intended intervals.

## Recommended Patterns

**Pattern 1: Calculate and use correct time boundaries for each window**
- For each requested window (e.g., 6h, 12h), subtract the window duration from the current time to get the correct start time.
- Issue a separate GET /Observation query for each window, using the correct `date=ge{start_time}` parameter.
- Example:
  - For "past 6 hours" at 2023-11-07T22:47:00+00:00, use `date=ge2023-11-07T16:47:00+00:00`.
  - For "past 12 hours" at the same time, use `date=ge2023-11-07T10:47:00+00:00`.

**Pattern 2: Extract and aggregate values only within each window**
- For each query, extract all values from the returned entries whose effective time is within the window.
- Calculate the summary statistic (e.g., average) for each window independently.
- If no data is found for a window, apply the default value rule (e.g., 'N/A').

**Pattern 3: Output results in the correct order**
- Ensure the output array or structure matches the order of the requested windows (e.g., [6h average, 12h average]).
- Do not swap or misalign the results.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S6352985."

**Step-by-step:**

1. Current time: 2023-11-07T22:47:00+00:00.
2. For 6h window: Subtract 6 hours → 2023-11-07T16:47:00+00:00.
   - GET /Observation?code=HEARTRATE&patient=S6352985&date=ge2023-11-07T16:47:00+00:00
3. For 12h window: Subtract 12 hours → 2023-11-07T10:47:00+00:00.
   - GET /Observation?code=HEARTRATE&patient=S6352985&date=ge2023-11-07T10:47:00+00:00
4. For each response, extract all `valueQuantity.value` fields within the window.
5. Calculate the average for each window. If no data, return 'N/A' for that window.
6. Output: FINISH([6h_average, 12h_average])

CORRECT output: `FINISH(["N/A", 78.2])` (if only 12h window has data)
WRONG output:   `FINISH(["N/A", "N/A"])` (if 12h window actually has data but was queried incorrectly)

## Success Indicators

- Each summary value corresponds to the correct, non-overlapping time window as requested.
- The agent issues distinct queries for each window with the correct `date=ge...` parameter.
- The output array matches the order and content of the requested windows, with 'N/A' only for truly missing data.

## Failure Indicators

- Both windows return 'N/A' when at least one window has data in the FHIR server.
- The same query is used for both windows, or the wrong start time is used for one window.
- The output order does not match the requested window order.
- Data from the wrong time window is included in the calculation.
