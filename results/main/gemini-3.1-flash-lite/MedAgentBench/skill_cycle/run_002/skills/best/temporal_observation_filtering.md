---
description: Enforce strict validation of observation search results against current
  system time before concluding data absence.
name: temporal_observation_filtering
provenance:
  action: MODIFY
  epoch: 7
  fixes: 1
  parent_version: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task5_7
  - task9_22
  - task9_8
  - task5_3
  - task9_20
  - task10_13
  - task10_16
  - task9_3
  - task10_21
  - task10_15
  update_cycle: 1
tags:
- fhir
- temporal
- observation
- validation
version: 2
---

## Skill Title
Temporal Observation Filtering and Verification

## Pattern Description
When searching for clinical observations (labs, vitals) within a specific time window (e.g., "last 24 hours"), you must not assume that an empty search result or a bundle with old entries implies the absence of data. You must explicitly compare the `effectiveDateTime` or `issued` field of every returned observation against the current system time provided in the task context.

If a search returns no results, you must verify if the search parameters were too restrictive or if you need to perform a broader search to confirm the absence of data before concluding that no measurement exists.

## When to Use This Skill
- When a task requires checking for a lab result within a specific timeframe (e.g., "last 24 hours").
- When a GET request for an Observation returns a `total: 0` or an empty `entry` array.
- When you are tempted to conclude "No [lab] found" without inspecting the `effectiveDateTime` of the returned resources.

## Common Failure Patterns
- Assuming `total: 0` in a FHIR bundle means no data exists for the patient, ignoring that the search might have been too narrow.
- Failing to compare the `effectiveDateTime` of the most recent observation to the current system time, leading to the use of stale data or incorrect "no data" conclusions.
- Returning a negative result (e.g., "No magnesium level found") without confirming that the search covered the relevant time window.

## Recommended Patterns

**Pattern 1: Search Validation**
If a search returns `total: 0`, do not immediately conclude no data exists. Check if your search parameters (like `code` or `patient`) are correct. If they are, perform a broader search (e.g., remove the time-based filter if you applied one in the URL) to see if any historical data exists, then filter it yourself.

**Pattern 2: Temporal Filtering**
For every observation in the bundle, extract the `effectiveDateTime`. Compare this value to the current system time. 
- If `current_time - effectiveDateTime <= 24 hours`, the result is valid.
- If all results are older than 24 hours, you must state that no result exists *within the last 24 hours*.

**Pattern 3: Negative Conclusion**
Only issue a negative `FINISH` (e.g., "No magnesium level recorded in the last 24 hours") after you have confirmed that no observations in the bundle meet the temporal criteria.

## Example Application

**Task:** "Check patient S0581164's last serum magnesium level within last 24 hours."

**Step-by-step:**
1. GET `.../Observation?code=MG&patient=S0581164`.
2. Inspect the bundle. If `total` is 0, verify the patient ID and code.
3. If results exist, iterate through `entry` and check `resource.effectiveDateTime`.
4. If the most recent `effectiveDateTime` is > 24 hours from the current time, conclude: `FINISH(["No magnesium level has been recorded in the last 24 hours."])`.

## Success Indicators
- Agent correctly identifies that data exists but is outside the requested window.
- Agent performs a broader search if the initial search returns no results.

## Failure Indicators
- Agent returns "No data found" when data exists but is older than the requested window.
- Agent fails to account for the current system time when evaluating the "last 24 hours" constraint.
