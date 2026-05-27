---
description: "Ensures a Patient search is performed and MRN extracted before answering\
  \ MRN\u2011lookup queries"
name: mrn_lookup_precondition
provenance:
  action: ADD
  epoch: 1
  fixes: 3
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task8_19
  - task9_22
  - task9_1
  - task2_6
  - task9_5
  - task10_27
  - task9_9
  - task5_3
  - task1_10
  - task9_8
  update_cycle: 1
tags:
- mrn
- patient_lookup
- precondition
version: 1
---

# MRN Lookup Precondition

## Pattern Description
You must always resolve a patient record before answering any question that asks for the patient’s MRN based on name and/or date of birth. The capability consists of constructing a precise FHIR Patient search, validating the response, extracting the identifier that represents the MRN, and returning it in the required `FINISH` format. This prevents the agent from skipping the lookup and emitting free‑text or reasoning instead of the exact identifier.

## When to Use This Skill
- The task description contains the phrase "MRN of the patient" **and** a name (given/family) and/or a birthdate (e.g., "What’s the MRN of the patient with name *John Doe* and DOB *1970‑01‑01*?").
- No prior `GET /Patient` request appears in the current execution trace.
- The task explicitly expects a JSON array containing either the MRN string or the literal "Patient not found".

## Common Failure Patterns
- Agent replies with reasoning text instead of issuing a `GET /Patient` request.
- Agent returns free‑text like `"The MRN is S123456"` rather than `FINISH(["S123456"])`.
- Agent never extracts the identifier field and finishes with an empty array or unrelated payload.
- Agent uses the wrong query parameters (e.g., only `identifier=` instead of `given=`/`family=`/`birthdate=`).

## Recommended Patterns
**Pattern 1: Build and issue the Patient search**
1. Parse the task description to obtain:
   - `given` name (first word after "name" or before the family name).
   - `family` name (last word after "name").
   - `birthdate` (ISO‑8601 date after "DOB" or "birthdate").
2. Issue a GET request:
   ```
   GET {api_base}/Patient?given={given}&family={family}&birthdate={birthdate}
   ```
   - Use exact case‑preserving values; URL‑encode if needed.
3. Verify the response is a `Bundle` with `total >= 1` and at least one entry.

**Pattern 2: Extract the MRN**
1. From the first entry (`entry[0].resource`), locate the identifier that represents the MRN. Typical patterns:
   - `identifier` array where `type.coding.code == "MR"` or `system` contains "mrn".
   - If no type hint, fall back to the first identifier value.
2. Extract `identifier.value` as a string `mrn`.

**Pattern 3: Return the result**
- If a patient was found and an MRN extracted:
  ```
  FINISH(["{mrn}"])
  ```
- If `total == 0` or no identifier could be resolved:
  ```
  FINISH(["Patient not found"])
  ```

## Example Application
**Task:** "What’s the MRN of the patient with name Joshua Martinez and DOB of 1967-03-11? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Parse: `given=Joshua`, `family=Martinez`, `birthdate=1967-03-11`.
2. Issue:
   ```
   GET http://localhost:8080/fhir/Patient?given=Joshua&family=Martinez&birthdate=1967-03-11
   ```
3. Suppose the response Bundle contains one entry with:
   ```json
   "identifier": [{"value": "S123456", "type": {"coding": [{"code": "MR"}]}}]
   ```
4. Extract `mrn = "S123456"`.
5. Return:
   ```
   FINISH(["S123456"])
   ```
   If the Bundle had `total: 0`, return `FINISH(["Patient not found"])`.

## Success Indicators
- A `GET` request to the Patient endpoint with `given`, `family`, and `birthdate` parameters appears **before** any `FINISH`.
- The final `FINISH` payload is a JSON array with a single string (the MRN) or the exact string "Patient not found".

## Failure Indicators
- The skill fires for unrelated tasks (e.g., age computation, lab lookup) and produces an unnecessary Patient GET.
- No Patient GET is made before `FINISH` for an MRN‑lookup task.
- The `FINISH` payload contains free‑text, numbers, or an array with more than one element.
- The extracted identifier is missing or incorrectly taken from a non‑MRN field.
