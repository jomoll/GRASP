---
description: Force a GET request before FINISH for any task that needs patient data,
  not just explicit lookup tasks
name: require_fhir_query_before_finish
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task10_13
  - task9_5
  - task9_22
  - task5_7
  - task10_10
  - task1_10
  - task5_3
  - task10_15
  - task10_18
  - task5_17
  update_cycle: 1
tags:
- patient
- query
- validation
version: 3
---

# Require FHIR Query Before Finish (enhanced)

## Pattern Description
You must ensure that any task which depends on patient information performs at least one FHIR GET request before issuing a `FINISH`. The rule is not limited to explicit "lookup" phrasing; it also applies when the instruction mentions an MRN, name, DOB, or asks for a value that must come from the server. By checking the agent’s action log for a `GET` that targets a `Patient` or related resource, you can prevent premature finishes that would return stale or fabricated data.

## When to Use This Skill
- When the instruction references a patient identifier (e.g., `MRN S123456`, `patient S123456`).
- When the instruction asks for a patient attribute (e.g., age, name, MRN lookup by name/DOB).
- When the instruction requests a lab value, vital sign, or any observation tied to a patient.
- When the agent is about to call `FINISH` without a preceding `GET` that includes `Patient` in the URL.

## Common Failure Patterns
- `FINISH` is called immediately after reasoning, with no preceding `GET` request.
- The only API call made is a `POST` (e.g., creating a ServiceRequest) and the agent skips the required patient lookup.
- The agent performs a `GET` on an unrelated resource (e.g., `Condition`) but never queries the `Patient` resource.

## Recommended Patterns
**Pattern 1: Verify patient data query before finish**
1. Scan the action list for any `GET` whose URL contains `/Patient` **and** includes either `identifier=`, `family=`, `given=`, or `birthdate=` parameters.
2. If such a GET is found, allow the `FINISH`.
3. If not found, **insert** a `GET http://{api_base}/fhir/Patient?identifier={MRN}` (or name/DOB query) before proceeding to `FINISH`.

**Pattern 2: Fallback when patient not found**
- After the GET, inspect the returned Bundle `total` field.
- If `total == 0`, output the prescribed "Patient not found" message and **do not** attempt further actions.

**Pattern 3: Formatting the final output**
- Always wrap the answer in a JSON array inside `FINISH([...])`.
- For simple scalar answers (e.g., MRN), return `FINISH(["S123456"])`.
- For error messages, return `FINISH(["Patient not found"])`.

## Example Application
**Task:** "What’s the MRN of the patient with name Joshua Martinez and DOB of 1967-03-11? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Detect that the task needs patient data → trigger this skill.
2. Issue `GET http://localhost:8080/fhir/Patient?family=Martinez&given=Joshua&birthdate=1967-03-11`.
3. Receive the Bundle; if `total > 0`, extract `entry[0].resource.identifier[0].value` as the MRN.
4. Call `FINISH(["Sxxxxxxx"])`.  If `total == 0`, call `FINISH(["Patient not found"])`.

**CORRECT output:** `FINISH(["S3228213"])`
**WRONG output:** `FINISH(["MRN is S3228213"])` (extra text) or `FINISH(["S3228213"])` without having performed the GET.

## Success Indicators
- A `GET` request to a `Patient` endpoint appears in the action log before the final `FINISH`.
- The `FINISH` payload contains only the required scalar or error string.
- The agent does not call `FINISH` when the patient lookup GET returns `total == 0` without first returning the error message.

## Failure Indicators
- `FINISH` is emitted with no preceding `GET /Patient`.
- The agent returns a fabricated MRN or a message that includes extra wording.
- The agent returns the correct MRN but skips the GET entirely.
