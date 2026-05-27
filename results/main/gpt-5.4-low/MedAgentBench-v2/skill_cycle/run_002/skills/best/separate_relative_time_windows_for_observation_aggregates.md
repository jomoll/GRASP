---
description: Compute each requested retrospective time window with its own explicit
  temporal filter or post-filtered subset.
name: separate_relative_time_windows_for_observation_aggregates
provenance:
  action: ADD
  epoch: 2
  fixes: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task8_26
  - task3_14
  - task10_16
  - task3_12
  - task3_19
  - task1_20
  - task2_30
  - task2_17
  - task2_26
  - task2_1
  update_cycle: 0
tags:
- observation
- time-window
- aggregation
- heart-rate
- fhir-search
version: 1
---

# Skill Title

Separate Relative Time Windows for Observation Aggregates

## Pattern Description

When a task asks for multiple retrospective summaries over different windows (for example, past 6 hours and past 12 hours), you must compute each window from data that actually falls inside that window. Do not issue one broad query and then reuse its aggregate as if it also answered the narrower window.

This matters most for Observation-based calculations such as averages, minima, maxima, counts, or trend comparisons. Your behavior should change from “one search, two answers” to “one explicit time filter per requested window, or one broad search plus exact timestamp-based sub-filtering before calculation.”

## When to Use This Skill

- When the instruction asks for 2 or more time-bounded summaries like “past 6 hours and past 12 hours”
- When you are averaging Observation values and the task provides a current time in the prompt context
- When your initial Observation search used only the largest window and you still need a result for a smaller window
- When a returned Bundle contains observations spanning a superset interval and you need separate answers for nested intervals

## Common Failure Patterns

- Using only `date=ge<12h_start>&date=le<now>` and then inventing or extrapolating the 6-hour result
- Returning `"No observations in the past 6 hours"` even though the only query covered 12 hours, not 6 hours
- Averaging all returned `entry[].resource.valueQuantity.value` values from a 12-hour search for both outputs
- Failing to compare each observation timestamp (`effectiveDateTime`, or equivalent effective field) against the narrower cutoff
- Mixing search criteria, such as querying `category=vital-signs` without also isolating the requested code when the task gives a specific code like `HEARTRATE`

## Recommended Patterns

**Pattern 1: compute explicit cutoffs for every requested window**
From the task’s stated current time, calculate each window start independently.

For example, if `now = 2023-11-07T22:47:00Z`:
- 6-hour start = `2023-11-07T16:47:00Z`
- 12-hour start = `2023-11-07T10:47:00Z`

Then either:
- issue two searches, one per window, or
- issue one 12-hour search and post-filter observations into a 6-hour subset using timestamps.

CORRECT: separate 6-hour and 12-hour sets before averaging  
WRONG: compute one 12-hour average and reuse it for the 6-hour answer

**Pattern 2: filter by observation timestamp, not bundle total**
For each returned Observation, inspect the actual time field used for clinical timing, usually `effectiveDateTime`. Include an observation in a window only if its timestamp is `>= window_start` and `<= now`.

If the API returns no 6-hour search results, verify whether that was truly a 6-hour query. If not, do not conclude there were no 6-hour observations.

**Pattern 3: return numeric aggregates in requested order**
After building each window-specific set, extract numeric values from `valueQuantity.value`, compute the mean for that set, and return the final answers in the exact order requested.

CORRECT: `FINISH([79.67, 80.8])` for `[6-hour average, 12-hour average]`  
WRONG: `FINISH([80.8, 79.67])`  
WRONG: `FINISH(["No heart rate observations in the past 6 hours", 80.0])` when you never actually isolated the 6-hour window

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S6227720. The code for heart rate is 'HEARTRATE'. Current time: 2023-11-07T22:47:00+00:00"

**Step-by-step:**

1. Compute cutoffs:
   - 6-hour start: `2023-11-07T16:47:00Z`
   - 12-hour start: `2023-11-07T10:47:00Z`
2. Issue exact queries, for example:
   - `GET /Observation?patient=S6227720&code=HEARTRATE&date=ge2023-11-07T16:47:00Z&date=le2023-11-07T22:47:00Z`
   - `GET /Observation?patient=S6227720&code=HEARTRATE&date=ge2023-11-07T10:47:00Z&date=le2023-11-07T22:47:00Z`
3. From each returned `entry[].resource`, extract `valueQuantity.value` as numbers.
4. Compute the average separately for each result set.
5. Return results in prompt order: 6-hour first, 12-hour second.

CORRECT output: `FINISH([78.5, 80.0])`  
WRONG output: `FINISH(["No heart rate observations in the past 6 hours", 80.0])` after only querying the 12-hour range

## Success Indicators

- You compute or state distinct window start times before averaging
- Your actions show two date-bounded Observation searches or one search plus explicit timestamp sub-filtering
- The final output contains one value per requested window in the correct order
- A “no observations” claim is supported by a search or filter for that exact window

## Failure Indicators

- Only the largest window was queried, but answers were produced for multiple windows
- The 6-hour result is identical to the 12-hour result because the same observation set was reused without verification
- You claim the smaller window has no data without ever applying the smaller cutoff
- You average all observations returned by the broader query without checking `effectiveDateTime` against each requested window
