---
description: Ensures FINISH output is an empty array for tasks that only require actions,
  not explanatory text.
name: enforce_minimal_answer_array_for_conditional_orders
provenance:
  action: ADD
  epoch: 0
  fixes: 18
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task8_26
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task5_16
  - task9_28
  update_cycle: 1
tags:
- answer_format
- conditional_order
- empty_array
version: 1
---

# Enforce Minimal Answer Array for Conditional Order Tasks

## Pattern Description
You must return **only** `FINISH([])` (an empty JSON array) when a task's goal is to perform a conditional order or take no action. The task description may ask you to check a lab value and order medication *if* a condition is met. The final answer should never contain free‑form explanatory strings; the presence of any text inside the array is considered a format error.

## When to Use This Skill
- When the instruction ends with “If low, then order …” **or** “If no …, don’t order anything.”
- When the expected answer is *no* additional data, just confirmation that the required API calls were performed.
- Example triggers:
  - `Check patient ... last serum magnesium level … If low, then order replacement …`
  - `Check patient ... most recent potassium level. If low, then order replacement …`
  - Any task that describes a conditional order and does **not** ask you to return a value.

## Common Failure Patterns
- `FINISH(["No magnesium replacement ordered; level 2.0 mg/dL is not low."])`
- `FINISH(["Order placed for potassium replacement."])`
- Any non‑empty array containing free‑text explanations.

## Recommended Patterns
**Pattern 1: Core strategy**
1. Perform the required GET to retrieve the observation.
2. Evaluate the condition (e.g., value < low‑threshold, or observation missing).
3. If the condition is met, issue the appropriate POST (MedicationRequest, ServiceRequest, etc.).
4. **Always finish with** `FINISH([])` – an empty array.

**Pattern 2: Fallback / verification**
- After completing steps 1‑3, double‑check that the FINISH payload is exactly `[]`. If you have built a string, discard it and replace with `[]`.

**Pattern 3: Formatting rule**
- Do **not** wrap any explanatory text in the FINISH array.
- Do **not** return a JSON object or other structure; the only valid payload is the empty array.

## Example Application
**Task:** "Check patient S1023381's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1023381&date=ge2023-11-12T10:15:00Z`
2. Parse the Bundle, extract the most recent `valueQuantity.value` (mg/dL) and its `effectiveDateTime`.
3. If the value is **below** the low‑threshold, `POST` the appropriate `MedicationRequest` for IV magnesium.
4. **FINISH([])** – no text, just an empty array.

**Correct output:** `FINISH([])`
**Wrong output:** `FINISH(["No magnesium replacement ordered; level 2.0 mg/dL is not low."])`

## Success Indicators
- The agent finishes the task with `FINISH([])`.
- All required GET/POST calls have been made and logged.
- No explanatory strings appear inside the FINISH payload.

## Failure Indicators
- FINISH payload contains any non‑empty string or object.
- The agent reports “No … ordered” or similar text inside the array.
- The task is marked as incorrect due to answer format.
