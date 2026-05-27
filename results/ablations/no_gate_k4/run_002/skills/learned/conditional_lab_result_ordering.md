---
description: "Add threshold\u2011based ordering logic for low/high lab values"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 11
  triggering_sample_ids:
  - task10_13
  - task9_5
  - task9_22
  - task5_7
  - task10_10
  - task1_10
  - task5_3
  - task10_15
  - task10_18
  - task5_17
  update_cycle: 1
tags: []
version: 12
---

# Conditional Lab Result Ordering

## Pattern Description
You must decide whether to place a replacement order based on the most recent lab value. The skill applies to any task that asks to *check a lab result and order a replacement if the value is out of a safe range*. It expands the original “skip ordering when missing or recent enough” rule to include explicit threshold comparison and order creation when the value is abnormal.

## When to Use This Skill
- When a task says *“If the last [lab] is low/high, order replacement …”*.
- When the task provides a numeric threshold (e.g., `< 1.5 mg/dL` for magnesium) or a clinical rule that can be inferred (e.g., HbA1c > 9%).
- When a recent observation exists (within the time window the task specifies).

## Common Failure Patterns
- Only checking for presence of a result and skipping ordering, never creating the ServiceRequest.
- Comparing the wrong field (`valueString` instead of `valueQuantity.value`).
- Ignoring the unit or using the wrong comparison direction.
- Posting an order but forgetting to include the required `code.coding[0].code` for the replacement medication.

## Recommended Patterns
**Pattern 1: Retrieve and evaluate the lab value**
1. `GET {api_base}/Observation?code={lab_code}&patient={MRN}&_sort=-date&_count=1`.
2. If `Bundle.total == 0` → **skip ordering** (go to Pattern 3).
3. Extract `valueQuantity.value` as a number and `valueQuantity.unit`.
4. Compare against the task‑provided thresholds:
   - `if value < low_threshold` → *low* case.
   - `if value > high_threshold` → *high* case.
5. If the value is within range → **no order**.

**Pattern 2: Create the replacement order**
1. Build a `ServiceRequest` with the appropriate replacement code (e.g., NDC for IV magnesium).
2. Include `authoredOn` set to the current task time, `status: "active"`, `intent: "order"`, `priority: "stat"`.
3. Set `subject.reference` to `Patient/{MRN}`.
4. POST the request.
5. Record a note indicating why the order was placed (e.g., "Magnesium 0.8 mg/dL – low, replacement ordered").

**Pattern 3: Finish output**
- If no order was placed, `FINISH(["no replacement ordered"])`.
- If an order was placed, `FINISH(["{value}{unit}", "{date}", "{note}"])`.

## Example Application
**Task:** "Check patient S1478444's last serum magnesium level within last 24 h. If low (<1.5 mg/dL), order replacement IV magnesium."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1478444&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z&_sort=-date&_count=1`
2. Bundle total = 1 → extract `valueQuantity.value = 1.2`, `unit = "mg/dL"`, `effectiveDateTime = "2023-11-12T14:20:00+00:00"`.
3. `1.2 < 1.5` → low → create ServiceRequest with magnesium replacement NDC.
4. POST the ServiceRequest.
5. `FINISH(["1.2 mg/dL", "2023-11-12T14:20:00+00:00", "magnesium low – replacement ordered"])`.

## Success Indicators
- The agent posts a `ServiceRequest` only when the lab value breaches the defined threshold.
- The FINISH output contains three elements (value, date, note) when an order is placed, or a single‑element array with the exact phrase "no replacement ordered" otherwise.

## Failure Indicators
- An order is posted without checking the numeric value.
- The comparison uses the wrong operator (e.g., `>` instead of `<`).
- FINISH returns a free‑text sentence or combines value and unit into one string without separating the date.
- The posted `ServiceRequest` lacks the correct replacement `code` or `subject` reference.
