---
description: Ensure both lower and upper date filters are used in Observation queries
  for time-windowed averages.
name: observation_date_range_filter_for_time_window_averages
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task9_5
  - task1_13
  - task8_19
  - task9_6
  - task3_27
  - task3_10
  - task3_12
  - task2_15
  - task3_17
  - task10_8
  update_cycle: 0
tags:
- fhir
- observation
- date-range
- time-window
- vital-signs
- query-construction
- statistical-calculation
version: 1
---

# Observation Date Range Filter for Time-Windowed Averages

## Pattern Description

When calculating statistics (such as averages) over a specific time window (e.g., "past 6 hours" or "past 12 hours") from FHIR Observation resources, you must restrict the query to only those Observations whose effective times fall within the exact window. This requires specifying both a lower and an upper bound in the `date` parameter of the Observation search. Using only a lower bound (e.g., `date=ge...`) will include all observations after that time, not just those within the window, leading to incorrect results.

This pattern is essential for any task that requires summary statistics or filtering of Observations within a defined time interval, such as recent vital sign trends or lab value monitoring.

## When to Use This Skill

- When the task requests an average, minimum, maximum, or count of Observation values over a specific time window (e.g., "past 6 hours", "last 24 hours").
- When constructing a FHIR Observation search for a time-bounded query, especially for vital signs like heart rate, blood pressure, or labs.
- When the instruction includes phrases like "over the past X hours/days" or "within the last Y hours".

## Common Failure Patterns

- Using only a lower bound in the `date` parameter (e.g., `date=ge2023-11-07T10:47:00+00:00`) and omitting the upper bound, causing inclusion of observations outside the intended window.
- Calculating averages or statistics on all returned values, not just those within the requested window.
- Failing to adjust the date range when the current time is provided in the task context.
- Using the wrong date field (e.g., `issued` instead of `effectiveDateTime`).

## Recommended Patterns

**Pattern 1: Constructing the Date Range**
1. Identify the current reference time from the task context (e.g., `Current time: 2023-11-07T22:47:00+00:00`).
2. Subtract the window size (e.g., 6 hours) from the reference time to get the lower bound.
3. Use the reference time as the upper bound.

**Pattern 2: Building the FHIR Query**
- Use both `ge` (greater than or equal) and `le` (less than or equal) prefixes in the `date` parameter:
  - `date=ge<lower_bound>&date=le<upper_bound>`
- Example for 6-hour window ending at 2023-11-07T22:47:00+00:00:
  - `date=ge2023-11-07T16:47:00+00:00&date=le2023-11-07T22:47:00+00:00`

**Pattern 3: Filtering and Calculation**
- After retrieving the results, ensure all included Observations have `effectiveDateTime` within the specified window.
- Calculate the average (or other statistic) only on these filtered values.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S1374652."

**Step-by-step:**

1. Reference time: 2023-11-07T22:47:00+00:00 (from context).
2. For 6-hour window:
   - Lower bound: 2023-11-07T16:47:00+00:00
   - Upper bound: 2023-11-07T22:47:00+00:00
   - GET: `GET /Observation?code=HEARTRATE&patient=S1374652&date=ge2023-11-07T16:47:00+00:00&date=le2023-11-07T22:47:00+00:00`
3. For 12-hour window:
   - Lower bound: 2023-11-07T10:47:00+00:00
   - Upper bound: 2023-11-07T22:47:00+00:00
   - GET: `GET /Observation?code=HEARTRATE&patient=S1374652&date=ge2023-11-07T10:47:00+00:00&date=le2023-11-07T22:47:00+00:00`
4. Extract `valueQuantity.value` from each Observation in the response.
5. Calculate the average for each window and report in the required format.

CORRECT output: `FINISH(["Average heart rate over the past 6 hours: 89.0 bpm", "Average heart rate over the past 12 hours: 87.5 bpm"])`
WRONG output:   `FINISH(["Average heart rate over the past 6 hours: 89.0 bpm", "Average heart rate over the past 12 hours: 89.0 bpm"])` (if both queries used the same lower bound)

## Success Indicators

- Observation search queries include both `date=ge...` and `date=le...` parameters matching the requested time window.
- Only Observations within the exact window are used in calculations.
- The reported statistics (average, min, max, etc.) reflect only the values from the correct time interval.

## Failure Indicators

- Only a single `date=ge...` parameter is present in the Observation query.
- The same set of Observations is used for multiple time windows, leading to identical results for different intervals.
- Observations outside the requested window are included in the calculation.
- The agent's output does not change when the window size changes in the instruction.
