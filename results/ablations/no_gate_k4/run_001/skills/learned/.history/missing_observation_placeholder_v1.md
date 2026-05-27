---
description: "Generate a human\u2011readable placeholder when an Observation search\
  \ returns no entries"
name: missing_observation_placeholder
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task3_14
  - task4_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Missing Observation Placeholder Handling

## Pattern Description
You must always verify that a GET request for an Observation returns at least one entry before trying to extract a value. When the FHIR server returns an empty Bundle (`total = 0`), the task usually expects a clear “no result” message rather than a raw sentinel like `-1`. This skill provides a reusable way to detect an empty result set, infer the intended placeholder wording from the task context (code, time window, patient ID, and any downstream ordering logic), and finish with a properly formatted response.

## When to Use This Skill
- After any `GET .../Observation?...` call where the task asks for the *most recent* or *last* value of a lab/measurement.
- The task may also include conditional logic such as “if no recent result, order a new test” or “if no result, do not order”.
- The response bundle has `"type": "searchset"` and `"total": 0` (or an empty `entry` array).

## Common Failure Patterns
- Returning the literal placeholder `"-1"` instead of a descriptive sentence.
- Ignoring the empty bundle and proceeding to downstream logic (e.g., ordering a test that should only be placed when a result is old).
- Using the wrong field to detect emptiness, e.g., checking `entry` without confirming `total`.

## Recommended Patterns
**Pattern 1: Detect empty Observation bundle**
1. Parse the JSON response from the GET request.
2. If `bundle.total === 0` **or** `bundle.entry` is undefined/empty, treat the result as *no observation*.
3. Extract the following context from the original task (if available):
   - `code` (e.g., `A1C`, `MG`).
   - `patient` identifier.
   - Any time filter (`date=ge…`).
   - Desired placeholder wording (often supplied in the task description).
4. Construct a sentence that:
   - States that no measurement was recorded in the requested window.
   - Includes the patient identifier.
   - Mentions the intended follow‑up action (or lack thereof).
5. Call `FINISH(["<sentence>"])` and **do not** proceed to any ordering logic unless the task explicitly says to order when the result is missing.

**Pattern 2: Conditional ordering when result is missing**
- If the task says *“If the lab value result date is greater than 1 year old, order a new test”* and the bundle is empty, treat the result as “no recent value” and **order** the test **only** if the wording explicitly permits ordering on *absence* (rare). Otherwise, finish with the placeholder and skip ordering.

**Pattern 3: Formatting the placeholder**
- Use the exact phrasing expected by the task, e.g.:
  - `"No serum magnesium level recorded in the last 24 hours for patient S1754095; no IV magnesium ordered."`
  - `"No HbA1c result found for patient S6488980; no new test ordered."`
- Do **not** embed raw numbers or JSON structures.

## Example Application
**Task:** “What’s the most recent magnesium level of the patient S1754095 within last 24 hours?”

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1754095&date=ge2023-11-12T10:15:00Z`
2. Parse response – `total: 0` → empty bundle.
3. Build placeholder: `"No serum magnesium level recorded in the last 24 hours for patient S1754095; no IV magnesium ordered."`
4. `FINISH(["No serum magnesium level recorded in the last 24 hours for patient S1754095; no IV magnesium ordered."])`

**Correct output:**
```
FINISH(["No serum magnesium level recorded in the last 24 hours for patient S1754095; no IV magnesium ordered."])
```
**Wrong output:**
```
FINISH(["-1"])
```

## Success Indicators
- The agent calls `FINISH` with a sentence that mentions *no measurement* and the patient ID.
- No subsequent `POST` for a ServiceRequest is made unless the task explicitly requires ordering on absence.
- The placeholder respects the time window and measurement code described in the task.

## Failure Indicators
- The agent finishes with `"-1"` or any non‑descriptive token.
- The agent proceeds to order a test despite the task only asking for a placeholder when no result exists.
- The placeholder omits the patient identifier or time window, making the answer ambiguous.

---
*Tags:* ["observation","empty_bundle","placeholder","conditional_order"]
