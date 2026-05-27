---
description: "Enforce concise list output for decision\u2011type tasks (order vs.\
  \ no\u2011order) instead of free\u2011text strings."
name: decision_task_answer_format
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task9_9
  - task10_12
  - task9_20
  - task10_8
  - task9_27
  - task9_3
  - task9_6
  - task9_5
  - task9_8
  update_cycle: 1
tags: []
version: 1
---

# Decision Task Answer Formatting

## Pattern Description
You must output a **machine‑readable list** for any task that asks you to *decide* whether to place an order, give medication, or perform a follow‑up. The answer should be either an empty list `[]` (no action required) or a list containing the resources you have already created (e.g., a `ServiceRequest` reference). Human‑readable sentences are not allowed because downstream consumers expect a strict data type.

## When to Use This Skill
- The task description contains conditional language such as **"If low, then order"**, **"If absent, do not order"**, or **"If the result is older than X, order a new test"**.
- The expected answer is a **raw boolean, numeric, ISO‑datetime, or a list of resources**, not a free‑text explanation.
- After performing any required `GET` queries and optional `POST` creations, you are about to call `FINISH`.

## Common Failure Patterns
- `FINISH(["No potassium replacement needed; latest level 3.8 mmol/L is above goal."])` – returns a list of strings instead of an empty list.
- `FINISH(["Order placed for replacement potassium."])` – returns explanatory text rather than `[]` or a list of created resources.
- Mixing a numeric result with a string, e.g., `FINISH([3.8, "mmol/L"])` when only the numeric value is required.

## Recommended Patterns
**Pattern 1: Determine need for an order**
1. Extract the relevant lab value from the `Observation` bundle (`valueQuantity.value`).
2. Compare against the clinical threshold (e.g., potassium < 3.5 mmol/L).
3. If the value is **below** the threshold, construct and `POST` the appropriate `ServiceRequest` (or `MedicationRequest`).
4. If the value is **above** the threshold, **do not** create any order.

**Pattern 2: FINISH payload**
- **When an order was placed**: `FINISH([{"reference":"ServiceRequest/xyz"}])` or simply `FINISH([])` if the caller only cares about the fact that the order exists (the POST already succeeded).
- **When no order is needed**: `FINISH([])` – an empty list signals “no action required”.

**Pattern 3: Avoid free‑text**
- **WRONG**: `FINISH(["Potassium replacement ordered."])`
- **CORRECT**: `FINISH([])` (no order) **or** `FINISH([{"reference":"ServiceRequest/12345"}])` (order created).

## Example Application
**Task:** "Check patient S6309742's most recent potassium level. If low, then order replacement potassium. Also schedule a morning serum potassium level for the next day at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S6309742`
2. Extract the latest value: `valueQuantity.value = 3.8` (mmol/L).
3. Compare: `3.8 >= 3.5` → **no replacement needed**.
4. No `POST` for replacement potassium.
5. (Optional) `POST` a `ServiceRequest` for the follow‑up potassium draw **only if the task explicitly requires it**.
6. `FINISH([])` – empty list indicates that no replacement order was issued.

**CORRECT output:** `FINISH([])`
**WRONG output:** `FINISH(["No potassium replacement needed; latest level 3.8 mmol/L is above goal."])`

## Success Indicators
- The agent finishes with `FINISH([])` when the condition for ordering is not met.
- When an order is required, the agent posts the `ServiceRequest` **before** calling `FINISH` and finishes with either an empty list or a list containing a reference to the created resource.
- No free‑text strings appear in the `FINISH` payload.

## Failure Indicators
- `FINISH` contains any string elements.
- The payload mixes data types (e.g., numbers with strings) when only a list of resources or an empty list is expected.
- The agent reports a decision in prose rather than using the prescribed list format.
