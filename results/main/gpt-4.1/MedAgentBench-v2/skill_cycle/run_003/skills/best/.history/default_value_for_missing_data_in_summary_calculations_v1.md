---
description: Provide a default value (e.g., 'N/A') when no data is available for summary
  calculations like average heart rate.
name: default_value_for_missing_data_in_summary_calculations
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task10_18
  - task2_6
  - task10_27
  - task4_10
  - task3_27
  - task3_17
  - task9_27
  - task2_14
  - task3_7
  - task3_30
  update_cycle: 1
tags:
- missing_data
- default_value
- summary_calculation
- output_format
version: 1
---

# Default Value for Missing Data in Summary Calculations

## Pattern Description

When performing summary calculations (such as averages, minimums, or maximums) over a time window, it is common for no relevant data to be found in the EHR for the requested period. In these cases, the agent should not simply state that the calculation cannot be performed or is unavailable. Instead, the agent must return a clear, standardized default value (such as 'N/A' or a specified placeholder) for each requested summary, so that downstream consumers can reliably interpret the result.

This pattern ensures that the output is always structured and machine-readable, even when data is missing, and avoids ambiguous or verbose explanations. It is especially important for tasks that expect a fixed number of outputs (e.g., average heart rate for both 6 and 12 hours) regardless of data presence.

## When to Use This Skill

- When a summary calculation (e.g., average, min, max) is requested for a specific time window and the relevant FHIR search (e.g., GET /Observation) returns no entries.
- When the task expects a value for each requested period (e.g., "average heart rate over the past 6 hours and the past 12 hours") but no data is found for one or more periods.
- When verifying the presence of required orders or prescriptions (e.g., naloxone for opioid orders) and none are found, but a status or value is still required in the output.

## Common Failure Patterns

- Returning a verbose explanation (e.g., "No heart rate observations were found... so the average cannot be calculated.") instead of a default value.
- Omitting the expected output fields entirely when data is missing.
- Returning null, empty arrays, or inconsistent output formats.
- Using inconsistent or non-standard placeholders (e.g., "not available", "unable to calculate", etc.).

## Recommended Patterns

Pattern 1: Use a Standard Default Value
- For each requested summary (e.g., average heart rate for 6h and 12h), if no data is found, return a standard placeholder such as 'N/A' or another value specified by the task.
- Ensure the output structure matches the expected format (e.g., a list of values, one per period).

CORRECT: `FINISH(["N/A", "N/A"])`
WRONG:   `FINISH(["No heart rate observations were found for patient S123 in the past 6 or 12 hours, so the average heart rate cannot be calculated."])`

Pattern 2: Consistent Output for Multiple Periods
- If the task requests multiple periods (e.g., 6h and 12h), return a value for each period, using the default where appropriate.

Pattern 3: Explicit Status for Order/Prescription Checks
- When verifying required orders (e.g., naloxone for opioids) and none are found, return an explicit status (e.g., 'N/A', 'No active opioid orders') in the output, not just a statement that no action is needed.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S2016972."

**Step-by-step:**

1. Issue GET /Observation?code=HEARTRATE&patient=S2016972&date=ge{start_time}
2. If the response Bundle has `total: 0` or no relevant entries for either period:
3. For each requested period (6h, 12h), set the average to 'N/A'.
4. Construct the output as a list of values, one per period.

CORRECT output: `FINISH(["N/A", "N/A"])`
WRONG output:   `FINISH(["No heart rate observations were found for patient S2016972 in the past 6 or 12 hours, so the average heart rate cannot be calculated."])`

**Task:** "Verify that every active opioid analgesic order for patient S6500497 has a matching naloxone prescription. If an opioid order is active without naloxone, create a naloxone order."

1. Issue GET /MedicationRequest?patient=S6500497&status=active&medication={opioid_codes}
2. If no active opioid orders are found, return an explicit status: `FINISH(["N/A"])` or `FINISH(["No active opioid orders"])` as specified by the task.

## Success Indicators

- The output always contains a value (real or default) for each requested summary or status, even when no data is found.
- The output uses a consistent, standard placeholder (e.g., 'N/A') for missing data.
- No verbose explanations or ambiguous statements are present in the output.

## Failure Indicators

- The output omits expected fields or returns only a narrative explanation.
- The output uses inconsistent or non-standard placeholders for missing data.
- The output format changes when data is missing (e.g., returns a string instead of a list of values).
