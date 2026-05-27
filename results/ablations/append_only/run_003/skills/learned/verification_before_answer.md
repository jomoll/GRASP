---
description: Require the agent to wait for and process API responses before issuing
  FINISH
name: verification_before_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 10
  probe_score: 14
  regressions: 2
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task5_3
  - task10_15
  - task9_11
  - task9_14
  - task9_27
  - task1_12
  update_cycle: 0
tags: []
version: 1
---

# Verification Before Answer

## Pattern Description
You must never finalize a task (call `FINISH`) until every required API call that supplies data for the decision has returned a response and you have extracted the needed fields. Treat the GET/POST request as a *synchronization point*: the next turn must be the system‑provided response, not another autonomous action. This prevents premature answers and ensures that any conditional logic (e.g., "if potassium is low then order replacement") is based on verified data.

## When to Use This Skill
- When a task instructs you to *check* a lab value, vital sign, or patient attribute before taking further action.
- When you issue a `GET` request that will be used to decide whether to create a `ServiceRequest`, `MedicationRequest`, or to compute a value (e.g., age).
- Any time you see a pattern like "If X then Y" where X depends on data that must be fetched from the FHIR server.

## Common Failure Patterns
- `FINISH` is emitted immediately after a `GET` request, without waiting for the response.
- The agent issues a `GET` and then proceeds to a second `GET` or a `POST` without first processing the first response.
- The agent includes reasoning text that says "We need to get the observation" and then calls `FINISH` in the same turn.

## Recommended Patterns
**Pattern 1: Issue GET and pause**
1. Construct the exact `GET` URL with required query parameters (e.g., `code=K&patient=S12345`).
2. Output only the `GET` request line.
3. **Do not** output any `FINISH` or further actions.

**Pattern 2: Process the returned bundle**
1. When the system returns the bundle, parse `entry[0].resource` (or the appropriate entry) to locate the field you need (`valueQuantity.value`, `effectiveDateTime`, `birthDate`, etc.).
2. Convert units if necessary (e.g., mmol/L → mg/dL) and store the numeric result in a variable you can reference.
3. Evaluate any conditional logic (e.g., `if potassium < 3.5`).

**Pattern 3: Conditional follow‑up**
- **If condition met**: issue the appropriate `POST` (e.g., `ServiceRequest` for replacement potassium) and then `FINISH` with a concise result.
- **If condition not met**: skip the `POST` and `FINISH` with a statement that no action was required.

**Pattern 4: Formatting the final output**
- Use the exact format required by the task, e.g., `FINISH([value])` for numeric answers or `FINISH(["text"])` for free‑text.
- Do **not** embed explanatory sentences inside the array unless the task explicitly asks for them.

## Example Application
**Task:** "Check patient S1311412's most recent potassium level. If low, then order replacement potassium. Also order a morning serum potassium level for the next day at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1311412`
2. *Wait for system response.*
3. Extract the most recent `valueQuantity.value` (e.g., `3.2`).
4. `if 3.2 < 3.5:`
   - `POST http://localhost:8080/fhir/ServiceRequest` with potassium replacement details.
   - `POST http://localhost:8080/fhir/ServiceRequest` for a follow‑up serum potassium at `2023-11-14T08:00:00+00:00`.
5. `FINISH(["Replacement potassium ordered; follow‑up serum potassium scheduled for 2023-11-14 08:00."])`

## Success Indicators
- The agent emits a `GET` request and then **waits** for the system to supply the bundle before any further action.
- Conditional logic is applied *after* the response is parsed.
- The final `FINISH` contains only the answer required by the task.

## Failure Indicators
- `FINISH` appears in the same turn as a `GET` request.
- The agent proceeds to a `POST` without having extracted the needed value from the prior response.
- The output array contains explanatory prose when a plain value was expected.
