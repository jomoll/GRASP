---
description: Translate internal reasoning into concrete FHIR API calls before proceeding,
  while allowing straightforward tasks to finish without an explicit verification
  step.
name: action_generation_from_reasoning
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 8
  regressions: 2
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task10_15
  - task9_11
  - task1_15
  - task9_14
  - task3_7
  update_cycle: 0
tags: []
version: 1
---

# Action Generation from Reasoning

## Pattern Description
You must never finish a task with only a reasoning narrative. Whenever your internal plan mentions needing data from the FHIR server (e.g., a Patient, Observation, or ServiceRequest), you must immediately emit the exact API call that satisfies that need. The agent operates in a turn‑based loop: **reason → action → response → next step**. Skipping the action leaves the downstream logic without the required data and leads to false answers or missing orders.

## When to Use This Skill
- When the instruction asks for a value that must be looked up (MRN, age, lab result, vital sign, etc.).
- When your reasoning includes a sentence like “We need to get the patient record” or “We should retrieve the latest Observation”.
- When the task involves a conditional decision that depends on a FHIR resource (e.g., order a test only if no recent result).
- Any time you start a response with a `reasoning_content` block instead of a `GET`/`POST` action.

## Common Failure Patterns
- Returning a JSON object that contains only a reasoning string and never issuing the described GET request.
- Emitting a GET for the wrong resource (e.g., `GET /Condition` instead of `GET /Patient`).
- Omitting required query parameters such as `identifier=`, `code=`, `patient=` or date filters.
- Using the wrong date prefix (`date=` instead of `date=ge...`).
- Finishing with `FINISH` before the required data has been retrieved **only when the task explicitly depends on that data**.

## Recommended Patterns
### Pattern 1: Immediate translation of the first data‑need into an API call
1. Parse the instruction and identify the first FHIR resource you need.
2. Construct the exact URL using the base URL from the context (`{api_base}`).
3. Include all required query parameters:
   - Patient lookup: `GET {api_base}/Patient?identifier=MRN` **or** `GET {api_base}/Patient?name=First%20Last&birthdate=YYYY-MM-DD`.
   - Observation lookup: `GET {api_base}/Observation?code=CODE&patient=MRN[&date=geYYYY-MM-DDThh:mm:ssZ]`.
   - Age calculation: first `GET` the Patient, then compute age from `birthDate`.
4. Emit the GET (or POST/PUT) request **as the next action** and wait for the response before any further reasoning.

### Pattern 2: Optional verification of the response
- **If the task outcome depends on the presence or value of the retrieved resource**, inspect the Bundle:
  - If `total = 0`, handle the “not found” case immediately (e.g., `FINISH(["Patient not found"])`).
  - If entries exist, extract the needed field (`identifier.value`, `valueQuantity.value`, `effectiveDateTime`, etc.) before continuing.
- **If the task is simply to create a new resource after a lookup (e.g., ordering a referral after confirming the patient identifier)**, you may proceed to the POST without an explicit check, provided the GET was correctly formed and the patient reference is syntactically valid.
- This flexibility prevents unnecessary failures on straightforward tasks while still encouraging safe handling when the result truly matters.

### Pattern 3: Formatting the final answer
- After all required data is gathered (or after a safe POST), format the answer exactly as the task expects (e.g., `FINISH(["5.8%","2022-09-09"])`).
- Do not embed explanatory text or units unless the specification explicitly asks for them.

## Example Application
**Task:** "What’s the MRN of the patient with name Julie Rodriguez and DOB of 1962-01-20? If the patient does not exist, the answer should be \"Patient not found\""

1. **Reasoning:** We need the patient resource matching name and birthdate.
2. **Action:** `GET http://localhost:8080/fhir/Patient?name=Julie%20Rodriguez&birthdate=1962-01-20`
3. **Response:** Bundle with `total = 0` → no patient.
4. **Finish:** `FINISH(["Patient not found"])`

**Correct output:**
```
GET http://localhost:8080/fhir/Patient?name=Julie%20Rodriguez&birthdate=1962-01-20
FINISH(["Patient not found"])
```

## Success Indicators
- The agent’s next line after a reasoning block is always a `GET` or `POST` request (unless the task is already complete).
- The request URL contains the correct resource type and all required query parameters.
- `FINISH` appears only after the necessary data has been retrieved **or** after a safe creation action that does not depend on the retrieved data.
- Subsequent steps use fields extracted from the response when the task logic requires them.

## Failure Indicators
- The agent outputs a reasoning JSON object without a following API call.
- The emitted request targets the wrong endpoint or omits needed parameters.
- The agent calls `FINISH` while the needed Bundle is still pending **and** the task outcome depends on that data.
- Conditional logic runs on placeholder values (e.g., `-1`) without first confirming the presence of real data when such confirmation is required.

## Guard Clauses for Regressions Fixed
- **Referral ordering (task8_9):** After a patient lookup, the agent may directly POST the `ServiceRequest` without an explicit check of `total`, because the task only requires the referral to be created.
- **Simple existence queries (task1_27, task4_11):** The agent can finish with the appropriate answer (`"Patient not found"` or `-1`) immediately after receiving the GET response, without a separate verification step, as long as the GET was correctly formed.

## Tags
[]
