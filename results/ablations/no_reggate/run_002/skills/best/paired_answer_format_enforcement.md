---
description: "Ensures FINISH returns separate list elements for tasks that require\
  \ paired answers (order + follow\u2011up observation)."
name: paired_answer_format_enforcement
provenance:
  action: ADD
  epoch: 1
  fixes: 4
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task9_22
  - task9_1
  - task4_28
  - task9_5
  - task9_9
  - task10_10
  - task5_3
  - task9_8
  - task10_13
  update_cycle: 1
tags:
- format
- pairing
version: 1
---

# Paired Answer Format Enforcement

## Pattern Description
You must guarantee that the final FINISH payload respects the structure implied by the task description when multiple answer components are required.  Tasks that ask to *pair* an order with a follow‑up observation, schedule, or any secondary action expect each component to be a distinct element in the JSON array, not a single concatenated string.  This pattern isolates each logical answer piece so downstream consumers can parse them reliably.

## When to Use This Skill
- The task text contains phrases like **"pair this order with"**, **"also schedule"**, **"in addition"**, or any wording that indicates more than one distinct result is needed.
- The expected answer includes multiple values (e.g., an order confirmation and a scheduled observation time).
- You notice the agent is about to call `FINISH` with a single string that bundles several messages together.

## Common Failure Patterns
- `FINISH(["Order placed; schedule observation at 8am"])` – a single string combines two required pieces.
- `FINISH(["No potassium replacement needed; most recent potassium is 3.9 mmol/L."])` – the task also asked for a paired future serum potassium order, but the response is a single message.
- Returning a list with one element when the task explicitly demands two separate outputs.

## Recommended Patterns
**Pattern 1: Identify required components**
1. Scan the task description for keywords **order**, **pair**, **schedule**, **next day**, **at**, etc.
2. Count how many distinct answer pieces are implied (usually two: the primary action and the secondary scheduled observation).

**Pattern 2: Build the FINISH payload as separate elements**
- **CORRECT**: `FINISH(["Potassium replacement ordered (NDC 12345‑6789)", "Morning serum potassium scheduled for 2023-11-14T08:00:00+00:00"])`
- **WRONG**: `FINISH(["Potassium replacement ordered; schedule morning serum potassium at 2023-11-14T08:00:00+00:00"])`

**Pattern 3: Handle the "no action" branch**
- If the primary condition is not met, still return a single‑element list that clearly states the outcome, without tacking on extra text.
- **CORRECT**: `FINISH(["No potassium replacement needed; most recent level is 3.9 mmol/L."])`
- **WRONG**: `FINISH(["No potassium replacement needed; schedule not required."])` (the schedule part is unnecessary and should be omitted).

## Example Application
**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S6474456`
2. `GET http://localhost:8080/fhir/Observation?code=K&patient=S6474456`
3. Extract the latest `valueQuantity.value` (mmol/L) from the Observation bundle.
4. If the value < 3.5, `POST` a `ServiceRequest` for potassium replacement and capture a confirmation string.
5. Compute the datetime for *next day at 08:00* (e.g., `2023-11-14T08:00:00+00:00`).
6. `POST` a second `ServiceRequest` for a serum potassium observation at that datetime and capture its description.
7. `FINISH(["Potassium replacement ordered (NDC 12345‑6789)", "Morning serum potassium scheduled for 2023-11-14T08:00:00+00:00"])`

If the potassium level is normal, skip steps 4‑6 and simply:
`FINISH(["No potassium replacement needed; most recent level is 3.9 mmol/L."])`

## Success Indicators
- The FINISH call returns a JSON array where each element corresponds to a single logical answer component.
- No element contains a semicolon‑separated combined message.
- When an order is placed, a second element describing the paired observation is present.

## Failure Indicators
- FINISH payload contains only one string while the task description demands multiple pieces.
- Elements are concatenated with punctuation (e.g., semicolons) instead of being separate list entries.
- The agent omits the secondary scheduled observation when the task explicitly asks for it.
