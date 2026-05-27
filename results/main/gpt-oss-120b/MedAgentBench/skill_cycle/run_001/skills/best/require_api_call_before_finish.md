---
description: Force a GET request before any FINISH when a task needs patient or observation
  data
name: require_api_call_before_finish
provenance:
  action: ADD
  epoch: 1
  fixes: 10
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task3_10
  - task9_28
  - task1_27
  - task10_24
  - task5_17
  - task9_6
  - task5_7
  - task9_27
  - task9_14
  - task9_20
  update_cycle: 0
tags: []
version: 1
---

# Require API Call Before FINISH for Data‑Dependent Tasks

## Pattern Description
You must never answer a question or complete a task that depends on FHIR data without first retrieving that data via a GET request. This rule applies whenever the instruction mentions a patient identifier, name/DOB, a lab/observation code, or any other resource that must be looked up before you can construct a response or a subsequent POST. By enforcing a GET‑first pattern you avoid "no_api_call_before_answer" failures and ensure that the information you return is based on the latest server state.

## When to Use This Skill
- When the task asks for a **patient MRN** given a name and/or date of birth.
- When the task asks for the **most recent value** of a lab/observation (e.g., HbA1c, magnesium, potassium).
- When the task requires **recording a new Observation** and you need the patient reference (MRN) first.
- When the task includes a conditional order that depends on a retrieved value (e.g., "if the last value is older than 1 year, order a new test").
- Any instruction that references a FHIR resource **without providing a full resource ID**.

## Common Failure Patterns
- `FINISH` is emitted immediately after the user instruction, with no preceding `GET`.
- The agent constructs a POST using a hard‑coded identifier instead of looking it up via `GET Patient?...`.
- The agent extracts a value from the task text rather than from the API response.
- Missing query parameters (e.g., forgetting `birthdate` in a patient search).

## Recommended Patterns
**Pattern 1: Identify required resource and issue GET**
1. Scan the task text for keywords: `patient`, `MRN`, `name`, `DOB`, `code=`, `observation`, `lab`.
2. Build the appropriate GET URL:
   - Patient by MRN: `GET {api_base}/Patient?identifier={MRN}`
   - Patient by name/DOB: `GET {api_base}/Patient?family={family}&given={given}&birthdate={YYYY-MM-DD}`
   - Observation by code/patient: `GET {api_base}/Observation?code={CODE}&patient={MRN}`
3. Emit the GET request **before any FINISH or POST**.

**Pattern 2: Verify GET response before proceeding**
- If the Bundle `total` is 0, decide on the fallback (e.g., answer "Patient not found" or skip ordering).
- If the Bundle contains entries, extract the needed field (e.g., `identifier.value` for MRN, `valueQuantity.value` for labs, `effectiveDateTime` for timestamps).

**Pattern 3: Continue with POST or FINISH only after successful GET**
- For recording an Observation: use the patient reference from the GET response (`Patient/{id}`) in the Observation `subject.reference`.
- For conditional ordering: compare the extracted date/value to the rule, then issue a POST ServiceRequest if needed.
- Finally, emit `FINISH` with the answer derived from the GET (or POST verification) data.

## Example Application
**Task:** "What’s the MRN of the patient with name Kevin Vasquez and DOB of 1953-11-19? If the patient does not exist, answer \"Patient not found\"."

**Step‑by‑step:**
1. Detect a patient lookup is required.
2. Issue: `GET http://localhost:8080/fhir/Patient?family=Vasquez&given=Kevin&birthdate=1953-11-19`
3. Parse the response Bundle. If `total == 1`, extract the identifier value (e.g., `entry[0].resource.identifier[?type.coding.code == "MR"].value`).
4. If an MRN is found, `FINISH(["S1234567"])`; otherwise `FINISH(["Patient not found"])`.

**Correct output:** `FINISH(["S1234567"])`
**Incorrect output:** `FINISH(["S1234567"])` **without** the preceding GET request.

## Success Indicators
- A `GET` line appears in the agent’s action list **before** any `FINISH` or `POST` for the same task.
- The `FINISH` payload contains data that can be traced back to fields in the GET response.
- Conditional orders are only posted after the GET confirms the condition.

## Failure Indicators
- `FINISH` is the first action for a data‑dependent task.
- The agent references identifiers or values that were never retrieved from the API.
- The GET request is missing required query parameters, leading to an empty Bundle.
