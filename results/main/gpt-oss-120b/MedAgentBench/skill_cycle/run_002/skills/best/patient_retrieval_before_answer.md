---
description: Enforce a GET Patient request before answering any question that needs
  patient data (age, MRN, etc.)
name: patient_retrieval_before_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 14
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task5_19
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task5_16
  - task9_28
  - task5_7
  - task9_8
  - task9_6
  update_cycle: 1
tags:
- patient
- "pre\u2011action"
- validation
version: 1
---

# Patient Retrieval Before Answer

## Pattern Description
You must never answer a question that depends on a Patient resource without first issuing a GET request to retrieve that patient. This rule applies to any task that asks for the patient’s age, MRN, demographic fields, or any derived value from the Patient resource. By always fetching the resource first, you guarantee that the answer is based on up‑to‑date data and avoid the "no_action_performed_before_answer" failure mode.

## When to Use This Skill
- When the instruction asks for the patient’s **age** given an MRN.
- When the instruction asks for the patient’s **MRN** given name/DOB or other identifiers.
- When any other **Patient attribute** (e.g., gender, birthDate) is required for the answer.
- When the task description mentions a **patient identifier** (MRN, identifier, name, birthdate) and expects a concrete value.

## Common Failure Patterns
- Agent returns a numeric age or MRN **without** a preceding `GET /Patient` call.
- Agent uses only internal reasoning or hard‑coded values instead of inspecting the FHIR response.
- Agent constructs the answer before confirming that the GET request succeeded (e.g., `total == 0`).

## Recommended Patterns
**Pattern 1: mandatory GET request**
1. Identify the patient lookup key from the task (e.g., `identifier=S2450227` or `family=Smith&given=John&birthdate=1970-01-01`).
2. Issue a GET request:
   ```
   GET {api_base}/Patient?identifier={MRN}
   ```
   or
   ```
   GET {api_base}/Patient?family={family}&given={given}&birthdate={birthdate}
   ```
3. Verify the response is a Bundle with `total >= 1`. If `total == 0`, answer "Patient not found" (or appropriate fallback).
4. Extract the needed field:
   - Age: compute `floor((now - Patient.birthDate) / 1 year)`.
   - MRN: read the first identifier where `type.coding.code == "MR"` or use the `identifier.value` that matches the query.
5. **Only after** successful extraction, construct the FINISH output.

**Pattern 2: fallback on missing patient**
- If the GET returns no entries, do **not** guess. Return the prescribed fallback (e.g., "Patient not found" or a sentinel value like `-1`).

**Pattern 3: output formatting**
- Age: `FINISH([<integer>])`
- MRN: `FINISH(["<MRN>"])`
- Fallback: `FINISH(["Patient not found"])` or `FINISH([-1])` as task specifies.

## Example Application
**Task:** "What's the age of the patient with MRN of S2450227?"

**Step‑by‑step:**
1. Issue `GET http://localhost:8080/fhir/Patient?identifier=S2450227`.
2. Receive Bundle, locate `entry[0].resource.birthDate` (e.g., `1948-04-12`).
3. Compute age: `2023-11-13` minus `1948-04-12` → `75` years (floor).
4. Return `FINISH([75])`.

**Correct output:** `FINISH([75])`
**Wrong output (pre‑action failure):** `FINISH([75])` without the preceding GET request.

## Success Indicators
- Every task that requires patient data shows a preceding GET request in the action log.
- The FINISH payload contains values derived from the GET response, not hard‑coded numbers.
- If the patient is not found, the agent returns the defined fallback instead of guessing.

## Failure Indicators
- FINISH is called immediately after reasoning with no GET action.
- The agent answers with a value but the previous GET either did not occur or returned `total == 0`.
- The answer format does not match the task’s expected type (e.g., string instead of integer for age).
