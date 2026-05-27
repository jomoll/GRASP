---
description: Provide a default value (e.g., 'N/A') when no data is available for summary
  calculations like average heart rate.
name: default_value_for_missing_data_in_summary_calculations
provenance:
  action: MODIFY
  epoch: 3
  fixes: 5
  parent_version: 1
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - task3_3
  - task8_29
  - task6_26
  - task1_13
  - task8_5
  - task4_27
  - task8_26
  - task10_15
  - task10_13
  - task3_29
  update_cycle: 0
tags:
- summary-calculation
- missing-data
- output-format
- default-value
- FHIR-Observation
version: 2
---

# Default Value and Output Formatting for Missing Data in Summary Calculations

## Pattern Description

When performing summary calculations (such as averages, minimums, or maximums) over a time window, it is common for no data to be available for some or all requested intervals. In these cases, you must provide a default value (such as 'N/A') for each missing interval, and ensure the output format matches the expected structure for the task (e.g., a list of values, one per interval). This skill ensures that missing data is handled gracefully and that the output is both informative and machine-readable.

This pattern is especially important for tasks that require multiple summary values (e.g., average heart rate over 6 and 12 hours), where some intervals may have data and others may not. The agent must not only substitute 'N/A' for missing data, but also ensure the output is a list of values in the correct order and type, matching the task's requirements.

## When to Use This Skill

- When a summary calculation (average, min, max, etc.) is requested over one or more time intervals and the FHIR search returns no data for one or more intervals.
- When the task expects a list of summary values (e.g., [avg_6h, avg_12h]) and some or all intervals have no data.
- When the FHIR Observation search returns an empty `entry` array or `total: 0` for the relevant code and time window.

## Common Failure Patterns

- Returning a single 'N/A' or a single summary value instead of a list matching the number of requested intervals.
- Returning a list of default values (e.g., ["N/A", "N/A"]) without context or explanation when data is missing for all intervals.
- Returning a string explanation instead of a structured list (e.g., "No data found" instead of ["N/A", "N/A"]).
- Returning the wrong data type (e.g., numbers as strings, or vice versa).
- Failing to match the output format expected by the task (e.g., wrong list length or order).

## Recommended Patterns

**Pattern 1: Check for Data in Each Interval**
- For each requested interval (e.g., 6h, 12h), issue a FHIR Observation search with the appropriate `date` parameter.
- If the response `Bundle.entry` is empty or `total` is 0 for an interval, record 'N/A' for that interval.
- If data is present, compute the summary (e.g., average) as required.

CORRECT: `[77.0, "N/A"]` (if only the first interval has data)
WRONG:   `"N/A"` (single value instead of list)

**Pattern 2: Output Formatting**
- Always return a list of values, one per requested interval, in the order specified by the task.
- Use the default value ('N/A') only for intervals with no data; otherwise, provide the computed value.
- Ensure the output type matches the task (e.g., numbers as floats, 'N/A' as a string).

**Pattern 3: Explanation (if required by task)**
- If the task expects only a list, do not add extra explanation. If a narrative is required, include it as a separate string or in the appropriate field.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S6500497."

**Step-by-step:**

1. Issue GET for 6h window:
   `GET /Observation?code=HEARTRATE&patient=S6500497&date=ge2023-11-07T16:47:00+00:00`
2. If response `total` is 0, record 'N/A' for 6h.
3. Issue GET for 12h window:
   `GET /Observation?code=HEARTRATE&patient=S6500497&date=ge2023-11-07T10:47:00+00:00`
4. If response `total` is 0, record 'N/A' for 12h.
5. Construct output as a list: `["N/A", "N/A"]`

CORRECT output: `FINISH(["N/A", "N/A"])`
WRONG output:   `FINISH("N/A")` or `FINISH(["No data found"])`

## Success Indicators

- The output is a list with the same number of elements as requested intervals.
- Each element is either the computed summary value (as a number) or the default value ('N/A') for missing data.
- The output matches the expected type and order for the task.

## Failure Indicators

- Output is a single value or string instead of a list.
- List length does not match the number of requested intervals.
- Default value is used for intervals with available data, or vice versa.
- Output type is inconsistent (e.g., numbers as strings, or 'N/A' as a number).
- Output includes extraneous explanation or is not machine-readable as required.
