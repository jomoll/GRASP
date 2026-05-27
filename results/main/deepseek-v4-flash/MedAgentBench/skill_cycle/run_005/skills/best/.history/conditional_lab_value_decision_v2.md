---
description: When a task says 'check if low' or 'if low then order', compare the value
  against the threshold and act accordingly
name: conditional_lab_value_decision
provenance:
  action: MODIFY
  epoch: 3
  fixes: 5
  parent_version: 1
  probe_score: 2
  regressions: 3
  triggering_sample_ids:
  - task5_7
  - task9_28
  - task1_15
  - task9_1
  - task2_6
  - task10_8
  - task10_20
  - task9_6
  - task10_27
  - task10_16
  update_cycle: 0
tags: []
version: 2
---

# Conditional Lab Value Decision

## Pattern Description

When a task instructs you to check a lab value and conditionally act based on whether it is low, high, or within range, you must first determine whether any observation exists. The absence of a lab value is a distinct state from having a value that is within normal range. You must treat "no observation found" as a separate branch in your decision logic, not as equivalent to "value is normal" or "no action needed."

This skill covers the full decision tree: (1) determine if any observation exists, (2) if it exists, extract the numeric value, (3) compare against the threshold, (4) execute the appropriate action for each branch.

## When to Use This Skill

- When a task says "if low, then order X" or "if high, then do Y"
- When a task says "check if [lab] is low" and provides a threshold or dosing instructions
- When a task says "if no [lab] has been recorded, don't order anything" or similar conditional on absence
- When a task says "if the lab value result date is greater than 1 year old, order a new lab test" — this includes the case where no lab exists at all (effectively infinitely old)

## Common Failure Patterns

- Returning `-1` or `["No replacement needed"]` when the search returns `total: 0` but the task says to order a new test if no recent result exists
- Treating an empty search result as equivalent to "value is normal" when the task has a specific action for "no data"
- Failing to distinguish between "no observation in the last 24 hours" (which may mean don't order) vs "no observation ever" (which may mean order a new one)
- Extracting a value from an observation but not comparing it against the threshold before deciding
- Using the wrong threshold (e.g., using 1.8 mg/dL for magnesium when the task specifies a different threshold)

## Recommended Patterns

**Pattern 1: Check for existence first**
Before extracting any value, check the `total` field in the Bundle response.
- If `total` is 0 or the `entry` array is empty, you have no data.
- Read the task carefully: does it say "if no [lab] has been recorded, don't order anything" or does it say "if no recent result, order a new test"?
- Act according to the task's specific instruction for the no-data case.

**Pattern 2: Extract and compare the value**
If observations exist, find the most recent one (by `effectiveDateTime` or `issued`).
1. Extract `valueQuantity.value` as a plain number (not a string with units).
2. Compare against the threshold specified in the task.
3. If the value is below the threshold, execute the "low" action (e.g., order replacement).
4. If the value is at or above the threshold, execute the "normal" action (e.g., no replacement needed).

**Pattern 3: Handle the no-data branch explicitly**
- If the task says "if no [lab] has been recorded in the last 24 hours, don't order anything" → return `-1` or `["No replacement needed"]`
- If the task says "if the lab value result date is greater than 1 year old, order a new lab test" → no observation means it's older than 1 year, so order the new test
- If the task says "if low, then order" with no explicit instruction for missing data → return `-1` to indicate no data available

## Example Application

**Task:** "What's the last HbA1C value in the chart for patient S2016972 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step-by-step:**

1. Issue GET with exact parameters: `GET /fhir/Observation?code=A1C&patient=S2016972`
2. Check the response: `"total": 0` — no observations found.
3. Apply the conditional logic: no observation means the result date is effectively infinitely old, which is greater than 1 year.
4. Order a new HbA1C lab test using the LOINC code 4548-4.

CORRECT output: `FINISH(["Ordered new HbA1C lab test"])` or similar confirmation
WRONG output: `FINISH([-1])` — this incorrectly treats "no data" as "no action needed"

**Task:** "Check patient S0581164's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step-by-step:**

1. Issue GET with date range: `GET /fhir/Observation?code=MG&patient=S0581164&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. Check the response: `"total": 1` — one observation found.
3. Extract `valueQuantity.value` from the most recent observation.
4. Compare against the threshold (typically 1.8 mg/dL for magnesium).
5. If below threshold, order replacement. If at or above, return no replacement needed.

CORRECT output (value normal): `FINISH(["No replacement needed"])`
CORRECT output (no data): `FINISH([-1])`

## Success Indicators

- The agent checks `total` or `entry` length before extracting values
- The agent correctly distinguishes between "no data" and "data present but normal"
- The agent reads the task's specific instruction for the no-data case and follows it
- The agent orders a new lab test when the task says to do so if no recent result exists

## Failure Indicators

- The agent returns `-1` when the task says to order a new test if no result exists
- The agent returns `["No replacement needed"]` when the search returned results but the value was actually low
- The agent orders replacement when the value is normal
- The agent fails to extract the numeric value and instead returns a string with units
