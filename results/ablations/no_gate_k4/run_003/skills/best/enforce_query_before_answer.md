---
description: Require a GET request for any task that needs patient data before issuing
  FINISH.
name: enforce_query_before_answer
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task4_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Enforce Data Retrieval Before Answer

## Pattern Description
You must never produce a final answer (`FINISH`) for a task that depends on patient‑specific information without first retrieving that information from the FHIR server. The central lesson is to treat every request for a value (age, lab result, MRN lookup, etc.) as a two‑step process: **query → extract → answer**. This prevents premature answers and ensures the agent always works with up‑to‑date data.

## When to Use This Skill
- Any instruction that asks for a patient attribute (e.g., age, gender, MRN) or a clinical observation (e.g., potassium level, HbA1c, magnesium).
- Tasks that require a decision based on a lab value (e.g., "If low, order replacement").
- When the instruction contains identifiers such as `MRN`, `patient`, `code`, or a date range that imply a FHIR lookup.

## Common Failure Patterns
- The assistant emits `FINISH([...])` without a preceding `GET …` request.
- The assistant extracts a value from the task description itself instead of from a server response.
- The assistant issues a `GET` after already answering, which is too late.

## Recommended Patterns
**Pattern 1: Identify required resource and issue GET before any answer**
1. Scan the instruction for keywords that map to FHIR resources (`patient`, `MRN`, `code`, `date`, `age`, `value`).
2. Determine the appropriate endpoint:
   - `Patient` when the task mentions an MRN or demographic lookup.
   - `Observation` when the task mentions a lab code (e.g., `K`, `MG`, `HbA1c`).
3. Construct the exact GET URL using the base URL and query parameters. Example:
   - `GET http://localhost:8080/fhir/Patient?identifier=S1234567`
   - `GET http://localhost:8080/fhir/Observation?code=K&patient=S1234567`
4. **Do not** emit any `FINISH` until the response is received.

**Pattern 2: Verify GET response before proceeding**
- If the response `total` is `0`, handle the “not found” case explicitly (e.g., answer "Patient not found" or "No recent potassium level recorded").
- If the response contains a bundle, extract the needed field (`valueQuantity.value`, `birthDate`, etc.) from the first entry.

**Pattern 3: Produce the final answer only after extraction**
- Use the extracted value to compute any derived result (age calculation, low‑value check, dosing decision).
- Format the answer exactly as required, e.g., `FINISH([3.5])` for a numeric lab value or `FINISH(["Patient not found"])` for missing data.

## Example Application
**Task:** "What's the age of the patient with MRN of S2863714?"

**Step‑by‑step:**
1. Detect that the task needs a patient demographic → need `Patient` resource.
2. Issue: `GET http://localhost:8080/fhir/Patient?identifier=S2863714`
3. Receive bundle, extract `birthDate` (e.g., `1970-04-15`).
4. Compute age relative to the current time (`2023-11-13`).
5. Emit: `FINISH([53])`

**Correct output:** `FINISH([53])`
**Wrong output (violates skill):** `FINISH(["The patient is 53 years old."])` without a prior GET.

## Success Indicators
- Every `FINISH` in a data‑driven task is preceded by a `GET` whose URL matches the needed resource.
- The agent extracts the value from the GET response, not from the instruction text.
- When the GET returns no entries, the agent returns the appropriate "not found" message instead of fabricating data.

## Failure Indicators
- `FINISH` appears before any `GET` for a task that mentions a patient or observation.
- The agent references a value that never appeared in a GET response.
- The agent proceeds to order medication or create a ServiceRequest without first confirming the lab value via a GET.
