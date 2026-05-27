---
description: Require at least two observations in the time window before reporting
  an average for vitals like heart rate.
name: observation_average_requires_multiple_values
provenance:
  action: MODIFY
  epoch: 2
  fixes: 3
  parent_version: 2
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - task9_6
  - task3_29
  - task2_1
  - task4_27
  - task3_3
  - task8_26
  - task3_7
  - task2_14
  - task3_27
  - task2_30
  update_cycle: 1
tags:
- observation
- average
- vitals
- minimum_values
- decision_logic
version: 3
---

# Observation Average Requires Minimum Values

## Pattern Description

When calculating the average of a vital sign (such as heart rate) over a specified time window, you must enforce a minimum requirement of at least two distinct observations within that window. This prevents reporting averages based on insufficient data, which can mislead clinical interpretation. The skill applies to any average calculation for time-bounded vitals or labs, not just heart rate.

## When to Use This Skill

- When instructed to calculate the average of a vital sign (e.g., heart rate, blood pressure) over a defined time window (e.g., past 6 hours, past 12 hours).
- When the FHIR Observation search returns zero or one value for the specified window.
- When the task expects a numeric average or a statement about average value.

## Common Failure Patterns

- Reporting an average when only one observation is available (e.g., "Average heart rate is 80 bpm" with only one value).
- Reporting 'no observations' without referencing the minimum requirement (e.g., "Cannot calculate average; no observations are available" instead of "Cannot calculate average; at least two values are required").
- Allowing an average calculation with only two values, when the minimum should be higher (if protocol requires more).
- Failing to state the minimum requirement in the output when insufficient data is present.

## Recommended Patterns

Pattern 1: Minimum Value Enforcement
- After retrieving observations for the specified window, count the number of valid values.
- If fewer than two values are present, do NOT calculate or report an average.
- Instead, respond: "Cannot calculate average [vital] over the past [window]; at least two values are required, but only [N] value(s) are available."

Pattern 2: Fallback for Zero Values
- If zero values are present, respond: "Cannot calculate average [vital] over the past [window]; no observations are available."
- Optionally, state the minimum requirement: "At least two values are required."

Pattern 3: Correct Average Calculation
- Only calculate and report an average if two or more values are present.
- List the values and their timestamps in the output for transparency.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S2450227."

**Step-by-step:**

1. Issue GET /Observation?code=HEARTRATE&patient=S2450227&date=ge[window_start]
2. Extract all values and timestamps within the window.
3. For each window:
   - If values.length < 2: Respond "Cannot calculate average heart rate over the past [window]; at least two values are required, but only [N] value(s) are available."
   - If values.length >= 2: Calculate average, respond "Average heart rate over the past [window] is [avg] bpm, based on values: [list values and timestamps]."

CORRECT output:
FINISH([
  "Cannot calculate average heart rate over the past 6 hours; at least two values are required, but only one value (80 bpm at 2023-11-09T21:41:00+00:00) is available.",
  "Average heart rate over the past 12 hours is 70 bpm, based on two values: 80 bpm at 2023-11-09T21:41:00+00:00 and 60 bpm at 2023-11-08T20:09:00+00:00."
])

WRONG output:
FINISH([
  "Average heart rate over the past 6 hours cannot be calculated; only one value (80 bpm at 2023-11-09T21:41:00+00:00) is available.",
  "Average heart rate over the past 12 hours is 70 bpm, based on two values: 80 bpm at 2023-11-09T21:41:00+00:00 and 60 bpm at 2023-11-08T20:09:00+00:00."
])

## Success Indicators

- Output explicitly states the minimum requirement for average calculation when insufficient data is present.
- No averages are reported for windows with fewer than two values.
- Values and timestamps are listed for transparency when an average is reported.

## Failure Indicators

- Output reports an average with only one value.
- Output omits the minimum requirement when insufficient data is present.
- Output reports 'no observations' without clarifying the minimum needed for average calculation.
