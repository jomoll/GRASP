---
description: Require at least two observations in the time window before reporting
  an average for vitals like heart rate.
name: observation_average_requires_multiple_values
provenance:
  action: MODIFY
  epoch: 1
  fixes: 2
  parent_version: 1
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task3_10
  - task4_10
  - task3_30
  - task8_29
  - task9_27
  - task3_16
  - task9_14
  - task10_12
  - task6_26
  - task3_29
  update_cycle: 0
tags:
- observation
- average
- vitals
- data sufficiency
- time window
version: 2
---

# Observation Average Requires Multiple Values

## Pattern Description

When calculating the average of a vital sign (such as heart rate) over a specified time window, you must ensure that at least two distinct observation values are present within that window. Reporting an average with only one or zero values is not statistically meaningful and does not meet clinical expectations. This rule applies to all time-windowed average calculations for vitals, not just heart rate.

If there are fewer than two observations in the requested window, you must not report an average. Instead, clearly state that there is insufficient data to calculate an average for that period. This prevents misleading outputs and ensures clinical safety.

## When to Use This Skill

- When a task requests the average of a vital sign (e.g., heart rate, blood pressure) over a defined time window (e.g., "past 6 hours").
- After retrieving FHIR Observation resources for the specified code and time window.
- When the number of valid observations in the window is less than two.

## Common Failure Patterns

- Reporting an average when only one observation is present (e.g., "Average heart rate over 6 hours is 89 bpm" when only one value exists).
- Reporting an average when no observations are present (e.g., returning 0 or null as the average).
- Failing to distinguish between zero, one, or multiple observations in the time window.
- Reporting the single value as the average, or echoing the value as if it were an average.
- Not providing a clear message about insufficient data.

## Recommended Patterns

**Pattern 1: Minimum Observation Count Check**
1. After retrieving all Observation resources for the specified code and time window, count the number of valid observations (i.e., those with a usable `valueQuantity.value`).
2. If the count is two or more, proceed to calculate and report the average as requested.
3. If the count is less than two (i.e., zero or one), do NOT calculate or report an average. Instead, return a message indicating insufficient data.

CORRECT:
- "Cannot calculate average heart rate over the past 6 hours; only one value (89 bpm at 2023-11-07T17:05:00+00:00) is available."
- "Cannot calculate average heart rate over the past 6 hours; no observations are available for this period."

WRONG:
- "Average heart rate over the past 6 hours is 89 bpm" (when only one value exists)
- "Average heart rate over the past 6 hours is 0 bpm" (when no values exist)

**Pattern 2: Explicit Data Sufficiency Messaging**
- When insufficient data is present, always state the number of available observations and the relevant time window in your message.
- If only one value is present, include its value and timestamp for transparency.

**Pattern 3: Output Formatting**
- For each requested time window, output either the calculated average (if two or more values) or a clear insufficiency message (if fewer).
- Do not mix single-value reporting with average reporting.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S1374652."

**Step-by-step:**

1. Issue GET requests for Observations with `code=HEARTRATE`, `patient=S1374652`, and `date=ge<window_start>` for each window.
2. For each window, count the number of returned Observations with a valid `valueQuantity.value`.
3. If count >= 2, calculate the mean and report it.
4. If count == 1, report: "Cannot calculate average heart rate over the past X hours; only one value (Y bpm at <timestamp>) is available."
5. If count == 0, report: "Cannot calculate average heart rate over the past X hours; no observations are available for this period."

CORRECT output:
```
[
  "Cannot calculate average heart rate over the past 6 hours; only one value (89 bpm at 2023-11-07T17:05:00+00:00) is available.",
  "Cannot calculate average heart rate over the past 12 hours; only one value (89 bpm at 2023-11-07T17:05:00+00:00) is available."
]
```

WRONG output:
```
[
  "Average heart rate over the past 6 hours is 89 bpm.",
  "Average heart rate over the past 12 hours is 89 bpm."
]
```

## Success Indicators

- The agent only reports an average when at least two observations are present in the time window.
- When fewer than two observations are present, the agent outputs a clear, specific message about insufficient data, including the number of available values and their timestamps if applicable.
- No averages are reported for windows with zero or one value.

## Failure Indicators

- The agent reports an average when only one or zero values are present.
- The agent echoes a single value as if it were an average.
- The agent fails to mention data insufficiency or does not specify the number of available observations.
- The agent returns a misleading or default value (e.g., 0 or null) as the average.
