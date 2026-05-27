---
description: "Require a concrete FINISH answer for data\u2011retrieval tasks even\
  \ when an order is also placed"
name: must_provide_final_answer
provenance:
  action: MODIFY
  epoch: 4
  fixes: 13
  parent_version: 1
  probe_score: 13
  regressions: 0
  triggering_sample_ids:
  - task9_9
  - task10_24
  - task9_14
  - task10_21
  - task10_20
  - task9_20
  - task4_28
  - task9_28
  - task9_1
  - task10_12
  update_cycle: 0
tags: []
version: 2
---

# must_provide_final_answer

## Pattern Description
You must always emit a `FINISH` response that includes the concrete data answer requested by the user, even if the task also requires creating or ordering FHIR resources. The presence of a POST/PUT action does **not** exempt the task from providing the final answer. This ensures that the agent reports the retrieved value (e.g., a lab result) before concluding, while still performing any required orders.

## When to Use This Skill
- When the instruction asks for a specific measurement (e.g., "most recent potassium level") **and** also includes an ordering action (e.g., "order replacement potassium if low").
- When the user expects a numeric or textual answer in the final output, regardless of side‑effects.
- When the task description contains phrases like "Check … level", "What’s the last … value", or "If low, then order …".

## Common Failure Patterns
- `FINISH([])` – an empty array is returned, omitting the required measurement.
- `FINISH(["Potassium is 3.5 mmol/L, within normal range."])` – answer wrapped in free‑text instead of the plain numeric value expected.
- No `FINISH` at all after completing POST requests.

## Recommended Patterns
**Pattern 1: Core answer extraction and emission**
1. Perform the required `GET` request to retrieve the observation.
2. Extract the numeric value from `valueQuantity.value` (or the appropriate field) **as a plain number**.
3. If the task also includes an order, execute the `POST`/`PUT` **after** extracting the value.
4. Emit `FINISH([<numeric_value>])`.  If the task explicitly asks for additional text, you may append a second element, e.g., `FINISH([3.5, "order placed"])`.

**Pattern 2: Handling missing measurements**
- If the GET bundle has `total: 0` or no entry within the required time window, emit the sentinel value defined by the task (e.g., `-1`) in the `FINISH` array.

**Pattern 3: Formatting rules**
- **CORRECT:** `FINISH([3.5])`
- **WRONG:** `FINISH([])` or `FINISH(["Potassium = 3.5 mmol/L"])`

## Example Application
**Task:** "Check patient S1311412's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1311412`
2. Parse the bundle, locate the latest `Observation.entry[0].resource.valueQuantity.value` → `3.5`.
3. Because the task includes ordering, issue the appropriate `POST` for the replacement medication and the follow‑up `ServiceRequest`.
4. Finally, emit `FINISH([3.5])` to report the potassium value.

## Success Indicators
- The final agent output is a `FINISH` call containing the expected numeric value (or sentinel) as the first array element.
- Any required `POST` actions are still performed, but they do not replace the `FINISH` answer.

## Failure Indicators
- `FINISH` contains an empty array or free‑text instead of the plain numeric value.
- No `FINISH` is emitted after completing the ordering steps.
- The numeric value is incorrectly extracted (e.g., includes units or is taken from the wrong field).
