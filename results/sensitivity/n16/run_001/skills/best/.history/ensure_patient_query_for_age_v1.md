---
description: "Require a Patient GET request before any *age\u2011calculation* task\
  \ that provides an MRN. This rule only activates when the task explicitly asks for\
  \ the patient\u2019s age (or a numeric year\u2011based value) and the expected answer\
  \ is a plain integer. It does **not** apply to other MRN\u2011based operations such\
  \ as creating ServiceRequests, Observations, etc."
name: ensure_patient_query_for_age
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task5_20
  - task5_3
  - task10_15
  - task9_11
  - task9_14
  - task9_27
  - task1_12
  - task4_20
  update_cycle: 0
tags: []
version: 1
---

# Ensure Patient Query Before Age Calculation (Narrowed Trigger)

## Trigger Condition
- The user task **must** contain an explicit request for the patient’s age, e.g., phrases like:
  - "age of the patient"
  - "how old is the patient"
  - "calculate the age"
  - "years old"
- The task must provide a **Medical Record Number (MRN)** or other patient identifier.
- The expected answer (as indicated by the user or by the evaluation rubric) is a **bare integer** (or a specific fallback string such as "Patient not found").
- If the task does **not** request an age (e.g., ordering a referral, creating a ServiceRequest, fetching observations), this skill does **not** fire.

## Recommended Pattern (when trigger condition is met)
1. **GET the patient** using the supplied MRN/identifier:
   ```
   GET {api_base}/Patient?identifier={MRN}
   ```
2. Verify the response is a `Bundle` with `total = 1`. If `total = 0`, finish with the exact fallback string required by the task (e.g., `FINISH("Patient not found")`).
3. Extract the `birthDate` string from the first entry:
   ```json
   "birthDate": "YYYY-MM-DD"
   ```
4. Parse the current time supplied in the task (ISO‑8601) and compute the age in whole years:
   ```python
   age = floor((current_time - birthDate).days / 365.25)
   ```
5. **FINISH** the integer **without any surrounding list, quotes, or explanatory text**:
   ```
   FINISH(45)
   ```

## Failure Indicators (to avoid false positives)
- No `GET /Patient` request appears before the final `FINISH`.
- The final `FINISH` payload is a list, string, or sentence instead of a scalar integer (or the exact fallback string).
- The age is derived from a field other than `birthDate`.
- The task does not explicitly request an age.

## Success Indicators
- The task description contains an age‑related keyword as defined in the trigger condition.
- A `GET /Patient` request using the exact MRN/identifier is issued before any `FINISH`.
- The final `FINISH` contains only the computed integer (or the required fallback string).

## Example (triggered)
**Task:** "What is the age of the patient with MRN S2874099? It's 2023-11-13T10:15:00+00:00 now."
**Steps:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. Extract `birthDate":"1978-04-22"`.
3. Compute age → 45.
4. `FINISH(45)`

## Example (not triggered)
**Task:** "Order orthopedic surgery referral for patient S1478444. Include the note …"
- No age‑related keyword, so this skill does **not** fire. The agent proceeds with the ServiceRequest creation as before.
