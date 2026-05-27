---
description: "Validate and replace placeholder observation codes with correct LOINC\
  \ identifiers **only for Observation resources** before FHIR queries. The skill\
  \ activates exclusively on GET requests to `/Observation` that contain a `code=`\
  \ query parameter. If the code is not a known LOINC identifier, it is looked up\
  \ in the built\u2011in vital\u2011sign mapping table and substituted. If no mapping\
  \ exists, the request proceeds unchanged and a fallback local filter is applied\
  \ after the GET. This guard prevents the skill from interfering with non\u2011Observation\
  \ resources such as MedicationRequest."
name: observation_code_validation
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task1_23
  - task6_3
  - task3_14
  - task4_11
  - task9_14
  - task3_7
  - task4_23
  - task2_28
  - task2_30
  - task6_26
  update_cycle: 0
tags: []
version: 1
---

# Observation Code Validation for Vital Signs

## Trigger Condition
- Activate **only** when the agent issues a `GET` request whose URL matches the pattern `/Observation` **and** includes a `code=` query parameter.
- Do **not** run for any other resource types (e.g., MedicationRequest, Condition, etc.).

## When to Use This Skill
- The task description or context provides a non‑LOINC placeholder (e.g., `HEARTRATE`, `BP_SYSTOLIC`).
- A GET request to `/Observation` with `code=` returns `total: 0` despite the patient having vital‑sign data.

## Core Validation and Substitution (Pattern 1)
1. Parse the placeholder description from the request URL or from the surrounding task text.
2. Look up the description in the internal mapping table (see below).
3. If a LOINC code is found, replace the placeholder in the URL with that LOINC code.
4. If no mapping exists, **do not modify** the request; let it proceed unchanged.

## Fallback Verification (Pattern 2)
- After the GET, if the response `Bundle.total` is `0`, re‑issue the request **without** the `code` filter, retrieve all vital‑sign observations, and locally filter the bundle for the desired observation by matching `code.coding.display` or `code.text`.

## Mapping Table (partial)
| Description               | LOINC Code |
|---------------------------|------------|
| heart rate                | 8867-4     |
| respiratory rate          | 9279-1     |
| body temperature          | 8310-5     |
| systolic blood pressure   | 8480-6     |
| diastolic blood pressure  | 8462-4     |
| oxygen saturation         | 59408-5    |
| glucose                   | 2339-0     |

## Output Formatting (Pattern 3)
- Return only the numeric value extracted from `valueQuantity.value` (apply unit conversion if needed).
- Do **not** include units or explanatory strings in the final `FINISH` payload.

## Example Application
**Task:** "Calculate the average heart rate over the past 6 hours for patient S6227720. The code for heart rate is 'HEARTRATE'."
1. Detect placeholder `HEARTRATE`.
2. Map to LOINC `8867-4`.
3. Issue `GET /Observation?category=vital-signs&code=8867-4&patient=S6227720&date=ge2023-11-07T16:47:00Z&date=le2023-11-07T22:47:00Z`.
4. Extract each `valueQuantity.value`.
5. Compute average and `FINISH([78.4])`.

## Success Indicators
- The GET URL contains a LOINC code from the mapping table.
- The response `total` > 0 for the intended observation.
- The final `FINISH` payload contains a numeric value or calculated statistic, not a message about missing observations.

## Failure Indicators
- The request still uses the placeholder code and returns `total: 0`.
- The `FINISH` output includes a descriptive error string instead of a numeric result.
- The extracted value includes units or text (e.g., `"78 bpm"`).

## Guard Clause
If the request URL does **not** match `/Observation` or lacks a `code=` parameter, the skill aborts and lets the original request proceed unchanged. This ensures tasks involving other resources (e.g., MedicationRequest) are unaffected.
