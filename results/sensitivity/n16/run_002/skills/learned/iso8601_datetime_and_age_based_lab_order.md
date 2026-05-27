---
description: "Validate Observation dates have full ISO\u20118601 datetime and order\
  \ repeat lab if >1\u202Fyear old"
name: iso8601_datetime_and_age_based_lab_order
provenance:
  action: ADD
  epoch: 3
  fixes: 6
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task4_7
  - task10_8
  - task10_18
  - task2_17
  - task2_14
  - task1_20
  - task1_15
  - task4_27
  - task10_24
  - task1_26
  update_cycle: 0
tags:
- datetime
- age_check
- lab_order
version: 1
---

# ISO8601 DateTime Validation and Age‑Based Lab Ordering

## Pattern Description
You must ensure that any lab Observation you retrieve provides a full ISO‑8601 datetime (e.g. `2023-11-12T10:15:00+00:00`).  Many FHIR servers return only the date component (`2023-11-12`).  A missing time part makes age calculations ambiguous and can cause the agent to skip required follow‑up orders.  This skill adds a verification step, normalises date‑only strings to midnight UTC, compares the result to the current time, and creates a repeat `ServiceRequest` when the most recent result is older than one year.

## When to Use This Skill
- When a task asks for the *latest* value of a lab Observation **and** includes a conditional “order a new test if the result is > 1 year old”.
- When the Observation bundle contains an `effectiveDateTime` (or `issued`) that may be a plain date string without a time component.
- When the required answer format is a two‑element array: `[numeric_value, "full‑datetime"]`.

## Common Failure Patterns
- Returning `"2023-11-12"` instead of `"2023-11-12T00:00:00+00:00"`.
- Using the wrong field (`issued` vs `effectiveDateTime`) and missing the timezone offset.
- Skipping the age check, so no repeat `ServiceRequest` is created even though the result is > 1 year old.
- Outputting the date as a plain string without the time component, causing the answer type to be wrong.

## Recommended Patterns
**Pattern 1: Retrieve and normalize the datetime**
1. Issue `GET {base}/Observation?code={LOINC}&patient={MRN}`.
2. From the first entry in the Bundle, read `effectiveDateTime` if present; otherwise fall back to `issued`.
3. If the extracted string matches `^\d{4}-\d{2}-\d{2}$` (date only), append `"T00:00:00+00:00"` to create a full ISO‑8601 datetime.
4. Parse the resulting string into a datetime object for comparison.

**Pattern 2: Age‑based ordering**
1. Compute the difference between the normalized observation datetime and the current task context time (`now`).
2. If the difference is **greater than 365 days**, construct a `ServiceRequest` to order the same lab using the LOINC code supplied in the task (e.g., `4548-4` for HbA1c).
3. POST the `ServiceRequest` with:
   ```json
   {
     "resourceType": "ServiceRequest",
     "status": "active",
     "intent": "order",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "{LOINC}", "display": "{Lab Name}" }] },
     "subject": { "reference": "Patient/{MRN}" },
     "authoredOn": "{now}"
   }
   ```
4. Verify the POST succeeded before proceeding.

**Pattern 3: Formatting the final answer**
- Return a two‑element array where the first element is the numeric lab value (extracted from `valueQuantity.value` or the appropriate field) and the second element is the **full** ISO‑8601 datetime string you normalised in Pattern 1.
- Example correct output: `FINISH([5.9, "2023-11-12T10:15:00+00:00"])`.
- Example wrong output: `FINISH(["5.9 %", "2023-11-12"])` (missing time, wrong type).

## Example Application
**Task:** “What’s the last HbA1C value for patient S1311412 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test.”

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S1311412`.
2. Extract `effectiveDateTime` → `"2022-10-05"` (date only).
3. Normalize to `"2022-10-05T00:00:00+00:00"` and parse.
4. Compare to `now = 2023-11-13T10:15:00+00:00`; difference > 365 days.
5. POST a `ServiceRequest` for LOINC `4548-4` (HbA1c) with `authoredOn = now`.
6. Extract the numeric value `5.9` from `valueQuantity.value`.
7. `FINISH([5.9, "2022-10-05T00:00:00+00:00"])`.

## Success Indicators
- The FINISH output contains a number and a datetime string that matches the pattern `YYYY‑MM‑DDTHH:MM:SS+00:00`.
- When the observation is older than one year, a `ServiceRequest` POST is performed and the response is verified.

## Failure Indicators
- FINISH returns a string date without a time component or includes the unit in the value.
- No `ServiceRequest` is created despite the observation being > 1 year old.
- The agent uses `issued` when `effectiveDateTime` is present and still omits the time zone.
