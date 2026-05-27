---
description: When patient search returns 0 results, try alternative search parameters
  before concluding not found
name: patient_search_fallback_strategy
provenance:
  action: ADD
  epoch: 0
  fixes: 10
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task1_6
  - task9_28
  - task9_1
  - task9_14
  - task10_24
  - task9_11
  - task9_9
  - task5_19
  - task2_6
  - task9_5
  update_cycle: 1
tags:
- patient_search
- fallback
- not_found_verification
version: 1
---

# Patient Search Fallback Strategy

## Pattern Description

When searching for a patient by name and birthdate returns zero results, the agent must not immediately conclude the patient does not exist. FHIR search parameters can be sensitive to exact formatting, name variations, and parameter combinations. Before returning "Patient not found", you must try alternative search strategies that may match the same patient through different query patterns.

This skill teaches a systematic fallback approach: when the primary search returns `"total": 0`, you should retry with simplified or alternative parameters before concluding the patient is absent from the system. The goal is to distinguish between "patient truly does not exist" and "search parameters did not match due to formatting or data entry differences."

## When to Use This Skill

- When a GET /Patient search returns `"total": 0` and the task asks you to find a patient by name and/or birthdate
- When the task instructs you to return "Patient not found" if the patient does not exist — this is exactly when you must be most careful
- When searching by full name (given+family) and birthdate together yields no results
- When the patient identifier (MRN) search returns zero results but the task expects a patient to exist

## Common Failure Patterns

- Using `name=Andrew%20Bishop` (full name in one parameter) instead of `given=Andrew&family=Bishop` — FHIR servers may parse these differently
- Birthdate format mismatch: the server may expect `birthdate=1963-01-29` but the stored date has a different format or time component
- Name variations: the patient may have a middle name, nickname, or different spelling stored
- Combining too many parameters: sometimes fewer parameters return results while more specific ones do not
- Immediately concluding "Patient not found" after a single failed search without attempting alternatives

## Recommended Patterns

**Pattern 1: Primary search with split name parameters**
When the task provides a full name like "Andrew Bishop", always split it into `given` and `family` parameters rather than using the `name` parameter:

CORRECT: `GET /Patient?given=Andrew&family=Bishop&birthdate=1963-01-29`
WRONG:   `GET /Patient?name=Andrew%20Bishop&birthdate=1963-01-29`

**Pattern 2: Fallback when primary search returns 0 results**
If the primary search returns `"total": 0`, try these alternatives in order:

1. Remove the birthdate parameter and search by name only: `GET /Patient?given=Andrew&family=Bishop`
2. If that returns results, check the birthdate of each returned patient to find the correct match
3. If name-only search also returns 0, try searching by family name only: `GET /Patient?family=Bishop`
4. If still 0, try the `name` parameter as a last resort: `GET /Patient?name=Bishop`

**Pattern 3: Verification before concluding "not found"**
Only after ALL of the above alternatives have been tried and returned 0 results should you conclude the patient does not exist. Document in your reasoning that you attempted multiple search strategies.

## Example Application

**Task:** "What's the MRN of the patient with name Andrew Bishop and DOB of 1963-01-29? If the patient does not exist, the answer should be 'Patient not found'"

**Step-by-step:**

1. Issue primary search with split parameters:
   `GET /Patient?given=Andrew&family=Bishop&birthdate=1963-01-29`
   
2. Response shows `"total": 0`. Do NOT conclude "not found" yet.

3. Try fallback 1 — remove birthdate, search by name only:
   `GET /Patient?given=Andrew&family=Bishop`
   
4. If this returns results, examine each patient's `birthDate` field to find the one matching 1963-01-29.

5. If still 0, try fallback 2 — search by family name:
   `GET /Patient?family=Bishop`

6. If still 0, try fallback 3 — use the `name` parameter:
   `GET /Patient?name=Bishop`

7. Only after all alternatives return 0 results, conclude:
   CORRECT output: `FINISH(["Patient not found"])`
   WRONG output:   `FINISH(["Patient not found"])` after only one search attempt

## Success Indicators

- Agent attempts at least 2-3 different search parameter combinations before concluding "Patient not found"
- Agent splits full names into `given` and `family` parameters
- Agent checks birthdates of returned patients when searching without birthdate filter
- Agent's reasoning shows awareness that search parameters may need adjustment

## Failure Indicators

- Agent immediately concludes "Patient not found" after a single search returning 0 results
- Agent uses `name=Full%20Name` parameter instead of `given` and `family`
- Agent does not attempt any fallback searches before returning the final answer
- Agent returns "Patient not found" when the patient actually exists but had a different name format in the system
