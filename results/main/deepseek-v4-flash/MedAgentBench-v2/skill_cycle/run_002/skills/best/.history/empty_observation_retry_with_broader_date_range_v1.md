---
description: When an Observation search returns zero results, retry with a broader
  date range before concluding no data exists.
name: empty_observation_retry_with_broader_date_range
provenance:
  action: ADD
  epoch: 3
  fixes: 4
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task10_27
  - task2_25
  - task10_20
  - task10_16
  - task1_10
  - task3_30
  - task3_1
  - task4_10
  - task1_27
  - task3_17
  update_cycle: 1
tags: []
version: 1
---

# Empty Observation Retry with Broader Date Range

## Pattern Description

When querying the Observation resource for vital signs or lab values, a date filter that is too restrictive can cause the server to return zero results even when relevant data exists for the patient. You must not immediately conclude that no data exists after a single empty response. Instead, systematically broaden the date range and retry before reporting that no observations were found.

The core capability is a fallback search strategy: when a targeted date-constrained Observation query returns `"total": 0`, you should retry with a wider date window (e.g., remove the date filter entirely or extend it to cover the patient's entire record). This prevents false negatives where data exists but falls outside the initial query window.

## When to Use This Skill

- When a GET /Observation request returns a Bundle with `"total": 0` and you are computing an average, retrieving a most recent value, or checking for the existence of a measurement.
- When the task specifies a time window (e.g., "past 6 hours", "past 12 hours", "past year") and the initial query with that window returns empty.
- When you are searching for vital signs (e.g., heart rate) or lab values (e.g., TSH, free T4) and the first attempt yields no results.

## Common Failure Patterns

- Querying with `date=ge<current_time_minus_6_hours>` and getting zero results, then immediately concluding "No heart rate observations found" — when data may exist from an earlier time period.
- Using a one-year date window for lab values and getting zero results, then reporting "No lab results found" — when older results exist that could still be relevant.
- Failing to distinguish between "no data in the specified window" and "no data at all for this patient."

## Recommended Patterns

**Pattern 1: Initial targeted query**
Issue the GET request with the date range specified in the task (e.g., `date=ge{time_window_start}`).

**Pattern 2: Retry with broader date range on empty result**
If the response has `"total": 0`, retry the same query **without the date parameter** to get all observations for that patient and code. If that also returns empty, then conclude no data exists.

CORRECT: First query `GET /Observation?patient=X&code=HEARTRATE&date=ge2023-11-07T10:47:00Z` returns 0. Then retry `GET /Observation?patient=X&code=HEARTRATE` (no date filter). If still 0, report no data.
WRONG: First query returns 0, immediately report "No heart rate observations found."

**Pattern 3: Compute from broader results**
If the broader query returns results, filter them client-side to the required time window and compute the requested metric (e.g., average over 6 hours).

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S2161163."

**Step-by-step:**

1. Issue initial query with the 6-hour window:
   `GET /Observation?category=vital-signs&patient=S2161163&code=HEARTRATE&date=ge2021-11-05T18:47:00+00:00`
   
2. Response: `{ "total": 0, ... }` — empty.

3. **Do not conclude yet.** Retry without the date filter:
   `GET /Observation?category=vital-signs&patient=S2161163&code=HEARTRATE`
   
4. If this also returns `"total": 0`, then report: `FINISH(["No heart rate observations found for patient S2161163."])`

5. If the broader query returns results, filter the entries by `effectiveDateTime` to only those within the past 6 hours and past 12 hours, compute the averages, and return them.

CORRECT output: `FINISH([3.5, 3.2])` (average heart rates for 6h and 12h)
WRONG output: `FINISH(["No heart rate observations found for patient S2161163 in the past 6 or 12 hours."])`

## Success Indicators

- After an empty initial Observation query, the agent issues a second query without the date parameter.
- The agent correctly computes the requested metric from the broader result set when data exists.
- The agent only reports "no data" after both the targeted and broad queries return empty.

## Failure Indicators

- The agent reports "No observations found" after a single empty query without retrying.
- The agent retries but uses the same restrictive date range, getting the same empty result.
- The agent retries with a broader date range but then fails to filter the results client-side to the required time window.
