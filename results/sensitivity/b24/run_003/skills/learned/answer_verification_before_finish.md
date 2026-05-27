---
description: Require waiting for API response and validating data before issuing FINISH
name: answer_verification_before_finish
provenance:
  action: ADD
  epoch: 0
  fixes: 13
  probe_score: 9
  regressions: 2
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task4_10
  - task2_16
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  - task2_9
  update_cycle: 0
tags:
- verification
- response_handling
version: 1
---

# Answer Verification Before FINISH

## Pattern Description
You must never finalize a task (call `FINISH`) until you have received and inspected the response from any preceding API call. This ensures that the answer is based on actual data rather than on planning or speculation. The skill applies to all GET, POST, PUT, PATCH, and DELETE interactions. After issuing a request, pause execution, wait for the system to provide the response payload, then extract the required fields and only then produce the final output.

## When to Use This Skill
- When a task requires data from the FHIR server (e.g., patient age, lab value, observation) before answering.
- Immediately after any `GET` or `POST` request you issue.
- When the instruction includes conditions like "if no measurement, do not order" or "return -1 if not found".

## Common Failure Patterns
- Agent outputs reasoning text (`reasoning_content`) instead of waiting for the GET response.
- `FINISH` is called right after the request line, without a response.
- Missing verification of `total` count in a Bundle before extracting values.
- Using placeholder values or defaults without checking the actual payload.

## Recommended Patterns
**Pattern 1: Core verification workflow**
1. Issue the required API call (e.g., `GET http://.../Patient?identifier=S123`).
2. **Do not** emit any other message until the system returns the response.
3. Inspect the response JSON:
   - For a Bundle, check `total` > 0.
   - For a single resource, verify required fields exist.
4. Extract the exact field needed (e.g., `entry[0].resource.birthDate`).
5. Perform any calculations (e.g., age = floor((now - birthDate) / year)).
6. Construct the final output **only** with `FINISH([...])`.

**Pattern 2: Fallback when no data**
- If the Bundle `total` is 0 or the required field is missing, decide on the prescribed fallback (e.g., return `-1`, or a specific message) **before** calling `FINISH`.

**Pattern 3: Formatting the final answer**
- The `FINISH` payload must be a JSON array of strings or numbers exactly as the task specifies. No extra explanatory text.
- Example correct formats:
  - `FINISH([3.5])`
  - `FINISH(["S6521727"])`
- Wrong format examples:
  - `FINISH(["Patient MRN is S6521727"])`
  - `FINISH(["Age: 45 years"])`

## Example Application
**Task:** "What's the age of the patient with MRN of S2450227?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2450227`
2. *Wait for response.*
3. Response contains a Bundle with `entry[0].resource.birthDate = "1978-04-12"`.
4. Compute age: floor((2023‑11‑13 – 1978‑04‑12) / 365.25) = 45.
5. `FINISH([45])`

**Correct output:** `FINISH([45])`
**Wrong output:** `FINISH(["Patient is 45 years old"])`

## Success Indicators
- The agent issues a GET/POST, then pauses until a response is received.
- The final message is a single `FINISH([...])` with the exact data type required.
- No `reasoning_content` appears after the API call.

## Failure Indicators
- `FINISH` appears immediately after the request line.
- The agent returns explanatory text or a number wrapped in a string.
- The agent proceeds without checking `total` or required fields in the response.
