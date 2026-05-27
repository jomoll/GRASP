---
description: Add date/value checks before ordering labs based on recent results
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 3
  triggering_sample_ids:
  - task10_20
  - task10_27
  - task9_28
  - task8_29
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task5_16
  - task9_11
  update_cycle: 0
tags: []
version: 4
---

# Conditional Lab Result Ordering

## Pattern Description
You must decide whether to place a new lab order only after you have examined the most recent Observation for the requested test. The decision hinges on two reusable checks:
1. **Result recency** – if a valid result exists within the allowed window (e.g., ≤ 1 year for HbA1c), do **not** order a new test.
2. **Result value** – for conditional replacement orders (potassium, magnesium, etc.) compare the numeric value against a clinically‑defined low‑threshold before ordering a replacement.
This pattern prevents unnecessary ServiceRequest or MedicationRequest creation and keeps the agent’s output concise.

## When to Use This Skill
- When a task asks for the *last* value of a lab (e.g., HbA1c) **and** says *"if the result is older than X, order a new test"*.
- When a task asks to *replace* an electrolyte (potassium, magnesium) **if** the most recent value is below a low‑limit.
- When the task provides a LOINC code for the lab to order and expects a scalar answer (value + date) **or** a conditional order.

## Common Failure Patterns
- Ordering a new ServiceRequest even though a recent Observation exists.
- Ignoring the `effectiveDateTime` field and treating any result as “old”.
- Comparing the whole `valueQuantity` string (e.g., "4.0 mEq/L") instead of the numeric `value`.
- Using the wrong threshold (e.g., 3.5 mEq/L for potassium when the protocol says 3.0 mEq/L).
- Returning a free‑text answer instead of a JSON list of scalars.

## Recommended Patterns
**Pattern 1: Retrieve and evaluate the most recent Observation**
1. Issue `GET {base}/Observation?code={LOINC}&patient={MRN}&_sort=-date&_count=1`.
2. If `total == 0` → treat as *no recent result*.
3. Extract `valueQuantity.value` as a number and `effectiveDateTime` as an ISO‑8601 timestamp.
4. Parse the current task context time (provided in the prompt) to a datetime.
5. Compute `ageDays = (now - effectiveDateTime).days`.

**Pattern 2: Apply the appropriate conditional rule**
- **Recency rule** (e.g., HbA1c): if `ageDays <= 365` → **skip ordering**; return the value and date.
- **Low‑value rule** (e.g., potassium < 3.5 mEq/L, magnesium < 1.5 mg/dL): if `value < threshold` → **place replacement order**; otherwise, **do not order**.

**Pattern 3: Construct the final output**
- If no order is needed, `FINISH(["{value}{unit}", "{date}"])`.
- If an order is required, first `POST` the appropriate `ServiceRequest` or `MedicationRequest`, then `FINISH(["order placed", "{value}{unit}", "{date}"])`.
- Always wrap scalar strings in a JSON list; never return free‑text sentences.

## Example Application
**Task:** "What’s the last HbA1c value for patient S0722219 and when was it recorded? If the result is > 1 year old, order a new HbA1c test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S0722219&_sort=-date&_count=1`
2. Response contains `valueQuantity.value = 6.5`, `valueQuantity.unit = "%"`, `effectiveDateTime = "2022-03-08T10:00:00+00:00"`.
3. Compute `ageDays = 401` (now = 2023‑11‑13). Since `ageDays > 365`, **order** a new test.
4. `POST http://localhost:8080/fhir/ServiceRequest` with LOINC 4548‑4.
5. `FINISH(["6.5%", "2022-03-08"])`.

If the same patient had a result dated `2023‑06‑01`, the agent would skip step 4 and only return the value/date.

## Success Indicators
- The agent never creates a ServiceRequest when a recent Observation (≤ threshold) is present.
- The agent extracts numeric `valueQuantity.value` and compares it to the correct low‑threshold before ordering a replacement.
- The final `FINISH` payload is a JSON list containing only the requested scalars (or an explicit "no order" message).

## Failure Indicators
- A `POST ServiceRequest` appears in the trace despite a recent result within the allowed window.
- The agent compares the full `valueQuantity` string (including unit) to a number, causing a type error.
- The `FINISH` output contains free‑text sentences or extra fields beyond the required scalars.
