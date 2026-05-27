---
description: "Return plain\u2011string MRN or \"Patient not found\" instead of JSON\
  \ objects"
name: patient_search_placeholder
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 3
  triggering_sample_ids:
  - task1_12
  - task1_20
  - task1_11
  - task1_16
  - task1_13
  - task10_10
  - task10_12
  - task10_13
  - task9_1
  - task1_26
  update_cycle: 1
tags: []
version: 4
---

# patient_search_placeholder

## Pattern Description
You must translate a FHIR Patient search result into the exact answer format the task expects.  When the task asks for the MRN (Medical Record Number) of a patient, the answer must be a JSON array containing a single **string** – either the MRN value or the literal text "Patient not found".  This skill replaces the previous placeholder that emitted an object with `mrn` and `message` fields, which caused `answer_format_wrong_type` failures.

## When to Use This Skill
- When a task asks *"What’s the MRN of the patient …?"* and provides a name and/or birthdate to locate the patient.
- When the task explicitly states a fallback string (e.g., "Patient not found") for missing patients.
- When the agent has just performed a `GET /Patient?...` request and received a FHIR Bundle response.

## Common Failure Patterns
- Returning `[{"mrn":null,"message":"Patient not found"}]` – wrong JSON type (object instead of string).
- Returning the whole Bundle or an array of identifiers instead of a single string.
- Omitting the fallback string and leaving the array empty.

## Recommended Patterns
**Pattern 1: Successful patient lookup**
1. Inspect the Bundle response field `total`.
2. If `total > 0`, locate the first entry's `resource.identifier` array.
3. Choose the identifier whose `type.coding.code` is `MR` (or, if none, take the first identifier).
4. Extract its `value` as a plain string.
5. Call `FINISH(["<mrn>"])`.

**Pattern 2: Patient not found**
1. If `total == 0`, do **not** attempt to read identifiers.
2. Call `FINISH(["Patient not found"])`.

**Pattern 3: Defensive fallback**
- If the Bundle is malformed or the identifier cannot be found, treat it as "not found" and output the fallback string.

## Example Application
**Task:** "What’s the MRN of the patient with name Margaret Kidd and DOB of 1982-08-24? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Issue `GET http://localhost:8080/fhir/Patient?name=Margaret%20Kidd&birthdate=1982-08-24`.
2. Receive Bundle. Suppose `"total": 0`.
3. Apply Pattern 2 → `FINISH(["Patient not found"])`.

**Correct output:** `FINISH(["Patient not found"])`
**Wrong output:** `FINISH([{"mrn":null,"message":"Patient not found"}])`

## Success Indicators
- The final `FINISH` call contains a JSON array with exactly one string element.
- The string is either the extracted MRN or the literal "Patient not found".
- No object literals appear in the answer array.

## Failure Indicators
- `FINISH` contains an object or multiple elements.
- The answer array is empty.
- The MRN is wrapped in additional JSON structure (e.g., `{"mrn":"12345"}`).
