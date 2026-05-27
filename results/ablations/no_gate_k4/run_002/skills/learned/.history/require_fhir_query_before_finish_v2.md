---
description: Enforce a GET request before FINISH for any task that needs patient data,
  especially age queries
name: require_fhir_query_before_finish
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task4_27
  - task9_9
  - task5_16
  - task9_27
  - task2_26
  - task5_19
  - task2_16
  - task10_24
  - task9_14
  - task10_21
  update_cycle: 0
tags: []
version: 2
---

# Require FHIR Query Before FINISH (Enhanced)

## Pattern Description
You must ensure that any task which requires external patient information performs an appropriate FHIR GET request before issuing a FINISH. This includes tasks that ask for a patient’s age, demographic details, or any derived value that depends on the Patient resource. The skill prevents premature FINISH calls that would omit necessary data retrieval.

## When to Use This Skill
- When the instruction asks for the **age** of a patient identified by MRN.
- When the task requests any **derived patient attribute** (e.g., age, gender) that is not directly supplied in the prompt.
- When the task mentions a **Patient identifier** (MRN, identifier) and expects a numeric or textual answer derived from the Patient resource.

## Common Failure Patterns
- Agent calls `FINISH` without a preceding `GET http://.../Patient?...` request.
- Agent performs a GET on an unrelated resource (e.g., Observation) before FINISH.
- Agent extracts the age from a cached value or assumes a constant, bypassing the FHIR query.

## Recommended Patterns
**Pattern 1: Detect need for patient data**
1. Scan the task description for keywords: `age`, `birthdate`, `MRN`, `identifier`, `patient`. 
2. If any are present, set a flag `requires_patient_query = true`.

**Pattern 2: Enforce GET request**
- If `requires_patient_query` is true, the next action must be a GET request to the Patient endpoint with either:
  - `identifier=<MRN>`
  - `?family=...&given=...&birthdate=...` (for name/DOB lookups)
- Example CORRECT request:
  ```
  GET http://localhost:8080/fhir/Patient?identifier=S1152319
  ```
- WRONG: No GET before FINISH, or GET to a different resource.

**Pattern 3: Verify response before FINISH**
1. After the GET, ensure the response Bundle has `total >= 1` and contains a Patient entry.
2. If the bundle is empty, abort with `FINISH(["Patient not found"])` or an appropriate error message.
3. Only after a successful GET may you compute the age and call FINISH.

## Example Application
**Task:** "What's the age of the patient with MRN of S1152319?"

**Step‑by‑step:**
1. Detect `age` + `MRN` → `requires_patient_query = true`.
2. Issue GET:
   ```
   GET http://localhost:8080/fhir/Patient?identifier=S1152319
   ```
3. Receive Bundle, extract `birthDate` from `entry[0].resource.birthDate`.
4. Compute age using the provided current time, round down.
5. FINISH with a scalar integer array:
   ```
   FINISH([86])
   ```

**CORRECT output:** `FINISH([86])`
**WRONG output:** `FINISH(["86"])` or `FINISH([86])` without the preceding GET.

## Success Indicators
- A GET request to the Patient endpoint appears in the action log before any FINISH.
- The GET URL includes either `identifier=` or the appropriate name/DOB query parameters.
- FINISH output is a scalar numeric array (e.g., `[86]`).

## Failure Indicators
- FINISH is called with no prior Patient GET.
- The GET request targets a non‑Patient resource.
- The FINISH payload contains a string or array of strings instead of a numeric value.

---

**Note:** This modification expands the original skill to explicitly cover age‑related queries, ensuring consistent enforcement across all patient‑data‑dependent tasks.
