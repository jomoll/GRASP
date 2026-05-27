---
description: Require at least two observations in the time window before reporting
  an average for vitals like heart rate.
name: observation_average_requires_multiple_values
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task10_27
  - task3_14
  - task3_7
  - task9_27
  - task4_27
  - task2_30
  - task6_26
  - task2_1
  - task3_30
  - task2_15
  update_cycle: 0
tags:
- observation
- average
- vitals
- data sufficiency
- time window
version: 1
---

# Observation Average Requires Multiple Values

## Pattern Description

When calculating the average of a vital sign (such as heart rate) over a specified time window, you must ensure that there are at least two distinct observations within that window. Reporting an average based on only one or zero values is misleading and does not reflect a true average. This skill prevents the agent from returning an average when insufficient data is present, and instead prompts the agent to report the lack of adequate observations.

This pattern is essential for time-windowed summary statistics (e.g., "average over past 6 hours") where the clinical meaning of an average requires more than one measurement. It also helps avoid over-interpreting sparse or missing data.

## When to Use This Skill

- When instructed to calculate an average (mean) of a vital sign (e.g., heart rate, respiratory rate, blood pressure) over a defined time window (e.g., "past 6 hours", "past 12 hours").
- After retrieving a list of Observation resources for the relevant code and patient, filtered by the appropriate date range.
- Before reporting or returning an average value for the requested period.

## Common Failure Patterns

- Calculating and reporting an average when only one observation is present in the time window.
- Reporting an average when no observations are present (should instead report inability to calculate).
- Failing to distinguish between the number of observations in different requested windows (e.g., 6h vs 12h).
- Reporting the value of a single observation as the "average" without clarification.

## Recommended Patterns

**Pattern 1: Check for Sufficient Observations**
1. After retrieving Observations for the specified code and time window, count the number of valid observations (e.g., entries in the Bundle).
2. If two or more observations are present, proceed to calculate the average as usual.
3. If only one observation is present, do NOT report an average. Instead, state that only one value is available and an average cannot be calculated.
4. If zero observations are present, state that no data is available for the requested period.

CORRECT: "Cannot calculate average heart rate over the past 6 hours; only one value (80 bpm at 2023-11-12T14:06:00+00:00) is available."
WRONG:   "Average heart rate over the past 6 hours: 80 bpm (1 value at 2023-11-12T14:06:00+00:00)"

**Pattern 2: Separate Checks for Multiple Windows**
- If the task requests averages for multiple windows (e.g., 6h and 12h), perform the above check separately for each window.
- It is possible to have sufficient data for one window but not the other; report accordingly for each.

**Pattern 3: Output Formatting**
- Clearly state when an average cannot be calculated due to insufficient data.
- If only one value is present, report the value and timestamp, but do not call it an average.
- If no values are present, state that no observations are available for the period.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S2450227."

**Step-by-step:**

1. Issue GET for 6-hour window:
   GET /Observation?code=HEARTRATE&patient=S2450227&date=ge2023-11-09T16:00:00+00:00
2. Count returned observations. If only one, do not calculate average; report only the value and timestamp.
3. Repeat for 12-hour window.
4. Construct output:

CORRECT output:
FINISH(["Cannot calculate average heart rate over the past 6 hours; only one value (80 bpm at 2023-11-12T14:06:00+00:00) is available.", "Cannot calculate average heart rate over the past 12 hours; only one value (80 bpm at 2023-11-12T14:06:00+00:00) is available."])

WRONG output:
FINISH(["Average heart rate over the past 6 hours: 80 bpm (1 value at 2023-11-12T14:06:00+00:00)", "Average heart rate over the past 12 hours: 80 bpm (1 value at 2023-11-12T14:06:00+00:00)"])

## Success Indicators

- The agent only reports an average when two or more observations are present in the requested window.
- When only one observation is present, the agent reports the value and timestamp, but does not call it an average.
- When no observations are present, the agent states that no data is available for the period.
- For multi-window tasks, the agent applies the check independently to each window.

## Failure Indicators

- The agent reports an average for a window with only one or zero observations.
- The agent fails to distinguish between insufficient data in different windows.
- The agent's output is misleading, suggesting an average was calculated when only one value was present.
