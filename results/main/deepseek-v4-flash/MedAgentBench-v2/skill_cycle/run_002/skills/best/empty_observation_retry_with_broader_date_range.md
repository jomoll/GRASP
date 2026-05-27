---
description: When Observation search returns zero results, retry with broader date
  range and alternative code systems
name: empty_observation_retry_with_broader_date_range
provenance:
  action: MODIFY
  epoch: 4
  fixes: 4
  parent_version: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task8_5
  - task3_29
  - task1_11
  - task2_30
  - task1_20
  - task8_7
  - task2_26
  - task8_21
  - task2_1
  - task1_15
  update_cycle: 0
tags: []
version: 2
---

# Observation Search Fallback Strategy

## Pattern Description

When an Observation search returns zero results, do not immediately conclude the data does not exist. The data may be stored under a different code system, different code value, or may exist outside the requested date range. You must systematically exhaust all reasonable search variations before concluding no data exists.

This skill applies to any Observation search where the initial query returns an empty `entry` array (total=0). The core lesson is: a single failed search is never sufficient evidence of absence.

## When to Use This Skill

- When a GET /Observation returns `"total": 0` in the response bundle
- When searching for vital signs (heart rate, blood pressure, temperature, etc.) and the initial code search fails
- When searching for lab values (TSH, FT4, glucose, etc.) and the initial code search returns zero results
- When the task specifies a code like "HEARTRATE" but the FHIR server may use LOINC codes (e.g., "8867-4")

## Common Failure Patterns

- Searching with `code=HEARTRATE` when the server stores heart rate under LOINC `8867-4`
- Searching with a date range that is too narrow, missing observations outside that window
- Giving up after one or two searches without trying alternative code systems
- Not checking if the code parameter accepts different coding systems (e.g., `http://loinc.org|8867-4`)
- Searching with `category=vital-signs` when the observation might be stored without that category

## Recommended Patterns

**Pattern 1: Broaden the date range first**
When the initial date-filtered search returns zero results, immediately retry without the date parameter:

CORRECT: `GET /Observation?patient=X&code=HEARTRATE` (no date filter)
WRONG:   Giving up after `GET /Observation?patient=X&code=HEARTRATE&date=ge2023-11-07T10:47:00+00:00` returns zero

**Pattern 2: Try alternative code systems**
If the search without date filter also returns zero results, try alternative code values. Common mappings:
- Heart rate: try `8867-4` (LOINC) if `HEARTRATE` fails
- TSH: try `3016-3` (LOINC) if `TSH` fails
- Free T4: try `3024-7` (LOINC) if `FT4` fails

CORRECT: `GET /Observation?patient=X&code=8867-4` (LOINC code for heart rate)
WRONG:   Only trying `code=HEARTRATE` and giving up

**Pattern 3: Remove category filter as fallback**
If the search includes `category=vital-signs` and returns zero, retry without the category parameter. Some servers may not populate the category field correctly.

**Pattern 4: Final verification before concluding**
Only after trying all of the above (no date filter, alternative codes, no category filter) should you conclude no data exists. Document which searches were attempted in your FINISH output.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S3032536."

**Step-by-step:**

1. Issue initial search with date range:
   `GET /Observation?category=vital-signs&patient=S3032536&code=HEARTRATE&date=ge2023-11-07T10:47:00+00:00`
   → Returns total=0

2. Retry without date filter:
   `GET /Observation?category=vital-signs&patient=S3032536&code=HEARTRATE`
   → Returns total=0

3. Try alternative LOINC code for heart rate:
   `GET /Observation?category=vital-signs&patient=S3032536&code=8867-4`
   → If results found, extract `valueQuantity.value` as numbers

4. If still zero, try without category filter:
   `GET /Observation?patient=S3032536&code=8867-4`

5. Only if all searches return zero, conclude no data:
   `FINISH(["No heart rate observations found for patient S3032536 after searching with codes HEARTRATE and 8867-4, with and without date/category filters."])`

CORRECT output: `FINISH([3.5])` (average heart rate as number)
WRONG output:   `FINISH(["No heart rate observations found for patient S3032536."])` (without trying alternative codes)

## Success Indicators

- Agent retries with broader date range when initial search returns zero
- Agent tries alternative code systems (LOINC codes) when the primary code fails
- Agent removes category filter as a fallback
- Agent documents which searches were attempted in the FINISH output

## Failure Indicators

- Agent gives up after one or two searches without trying alternative code systems
- Agent concludes "no data" when data may exist under a different code
- Agent repeatedly searches with the same parameters that already returned zero
