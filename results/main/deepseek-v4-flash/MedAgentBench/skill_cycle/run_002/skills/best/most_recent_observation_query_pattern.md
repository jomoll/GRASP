---
description: Always use _sort=-date&_count=1 when querying for the most recent observation
name: most_recent_observation_query_pattern
provenance:
  action: ADD
  epoch: 0
  fixes: 10
  probe_score: 10
  regressions: 2
  triggering_sample_ids:
  - task2_26
  - task10_20
  - task9_9
  - task2_22
  - task4_28
  - task10_8
  - task10_15
  - task4_15
  - task2_28
  - task2_17
  update_cycle: 0
tags: []
version: 1
---

# Most Recent Observation Query Pattern

## Pattern Description

When a task asks for the "last", "most recent", or "latest" observation value for a patient, you must always include FHIR search parameters that guarantee you receive only the single most recent result. Without explicit sorting and limiting, the server may return observations in an arbitrary order, and you risk picking a stale or incorrect value.

The core pattern is to append `_sort=-date&_count=1` to any GET /Observation query where the goal is to find the most recent measurement. The `_sort=-date` parameter orders results by `effectiveDateTime` descending (newest first), and `_count=1` limits the response to a single entry. This ensures the first (and only) entry in the bundle is the most recent observation.

## When to Use This Skill

- When the task asks for the "last" or "most recent" lab value (e.g., HbA1C, magnesium, potassium, blood pressure)
- When the task asks for a value "within the last X hours/days" and you need the most recent one in that window
- When the task asks for the "latest" observation of a specific type
- When you need to check if an observation date is older than a threshold (e.g., >1 year old) and the most recent value is required

## Common Failure Patterns

- Querying `GET /Observation?code=A1C&patient=S0722219` without `_sort=-date&_count=1` — the server may return multiple entries in arbitrary order, and the agent picks the wrong one
- Assuming the first entry in the bundle is the most recent without sorting — the server default order is not guaranteed to be chronological
- Using `_sort=date` (ascending) instead of `_sort=-date` (descending), which returns the oldest first
- Forgetting `_count=1` and then manually iterating through entries to find the most recent, which is error-prone

## Recommended Patterns

**Pattern 1: Query for the most recent observation**

1. Construct the GET URL with the observation code, patient ID, and the sort/limit parameters.
2. Always use `_sort=-date&_count=1` in the query string.
3. If a date range is also needed (e.g., "within last 24 hours"), add `date=ge<start>&date=le<end>` but keep `_sort=-date&_count=1`.

CORRECT: `GET /Observation?code=A1C&patient=S0722219&_sort=-date&_count=1`
WRONG:   `GET /Observation?code=A1C&patient=S0722219`

**Pattern 2: Extract the value and date from the response**

1. Check that `entry` array is non-empty.
2. From the first (and only) entry, extract `resource.effectiveDateTime` for the date.
3. Extract the numeric value from `resource.valueQuantity.value` (preferred) or `resource.valueString` if no quantity is present.
4. Do not include units in the numeric value unless the task explicitly asks for them.

**Pattern 3: Handle empty results**

If `total` is 0 or `entry` is empty, return the appropriate sentinel value (e.g., -1) or message (e.g., "No observation found") as specified by the task.

## Example Application

**Task:** "What's the last HbA1C (hemoglobin A1C) value in the chart for patient S0722219 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step-by-step:**

1. Issue GET with sort and limit:
   `GET /Observation?code=A1C&patient=S0722219&_sort=-date&_count=1`

2. The response bundle will contain at most 1 entry, which is the most recent HbA1C.

3. Extract:
   - `entry[0].resource.effectiveDateTime` → e.g., "2022-03-08T08:14:00+00:00"
   - `entry[0].resource.valueQuantity.value` → e.g., 6.5

4. Compare the date to the current time (2023-11-13T10:15:00+00:00). Since 2022-03-08 is more than 1 year ago, order a new HbA1C lab using LOINC code 4548-4.

CORRECT output: `FINISH([6.5, "2022-03-08T08:14:00+00:00"])` then order the lab
WRONG output:   `FINISH([6.5, "2022-03-08T08:14:00+00:00"])` without checking the date (if >1 year, must order)

## Success Indicators

- The agent's GET request includes `_sort=-date&_count=1` when querying for the most recent observation
- The agent correctly extracts the value and date from the single returned entry
- The agent correctly handles empty results (returns -1 or appropriate message)

## Failure Indicators

- The agent's GET request omits `_sort=-date&_count=1` and relies on server default ordering
- The agent picks a non-most-recent observation from a multi-entry bundle
- The agent fails to check the date against the threshold (e.g., >1 year) and skips ordering when required
