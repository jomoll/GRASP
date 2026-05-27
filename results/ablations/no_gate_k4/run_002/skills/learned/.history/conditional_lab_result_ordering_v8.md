---
description: "Add explicit threshold check and follow\u2011up creation for low lab\
  \ results"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 7
  triggering_sample_ids:
  - task9_9
  - task10_15
  - task1_7
  - task4_21
  - task4_10
  - task10_16
  - task2_6
  - task4_26
  - task2_26
  - task4_11
  update_cycle: 1
tags: []
version: 8
---

# Conditional Lab Result Ordering with Threshold Evaluation

## Pattern Description
You must treat any task that asks "If the lab value is low/high, then order X and optionally schedule a follow‑up" as a two‑step decision process. First, extract the numeric result from the most recent Observation, compare it against the clinically‑relevant threshold supplied in the task description (or a default reference range if none is given), and only then create the replacement ServiceRequest. Second, if the task also requests a paired follow‑up test, invoke the `follow_up_lab_ordering` skill to schedule it.

- The skill is reusable for any lab code (e.g., potassium, magnesium, HbA1c) and any replacement medication or test.
- It centralises the conditional logic so the agent never finishes without evaluating the lab value.

## When to Use This Skill
- When a task contains a conditional clause such as "If low, then order replacement ...".
- When the task mentions a specific lab code (e.g., `code=K` for potassium) and a replacement NDC or medication.
- When the task also asks for a paired follow‑up lab (e.g., "order a morning serum potassium level tomorrow at 8 am").

## Common Failure Patterns
- Agent performs the GET request for the Observation but proceeds directly to `FINISH` without inspecting the value.
- Agent extracts the value as a string with units (e.g., `"3.5 mmol/L"`) and compares it to a numeric threshold, causing a type mismatch.
- Agent creates the replacement order unconditionally, even when the lab value is normal.
- Agent omits the required follow‑up order when the replacement is placed.

## Recommended Patterns
**Pattern 1: Extract and evaluate the lab value**
1. Issue a GET request for the most recent Observation of the requested code, sorted by `-date` and limited to 1.
2. From the returned Bundle, locate `entry[0].resource.valueQuantity.value` (numeric) and `valueQuantity.unit`.
3. Convert the value to the unit expected by the threshold if necessary (e.g., mmol/L → mEq/L for potassium).
4. Compare the numeric value to the threshold defined in the task (e.g., `< 3.5`).
5. If the condition is true, proceed to Pattern 2; otherwise, `FINISH(["no replacement ordered"])`.

**Pattern 2: Create replacement order and optional follow‑up**
1. Build a `ServiceRequest` with the replacement NDC or medication code, referencing the patient.
2. POST the ServiceRequest.
3. If the task mentions a paired follow‑up lab, call the existing `follow_up_lab_ordering` skill with the appropriate code and schedule.
4. `FINISH(["replacement ordered"] )` (or include both actions in the array).

**Pattern 3: Formatting the FINISH output**
- Use a plain array of strings; do not embed JSON objects or extra commentary.
- Example correct output: `FINISH(["potassium replacement ordered", "follow‑up potassium test scheduled for 2023‑11‑14T08:00:00+00:00"])`.

## Example Application
**Task:** "Check patient S6309742's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S6309742&_sort=-date&_count=1`
2. Extract `valueQuantity.value = 3.2` and `unit = "mmol/L"`.
3. Convert to mEq/L if needed (1 mmol/L = 1 mEq/L for K). Compare: `3.2 < 3.5` → condition true.
4. POST a `ServiceRequest` for the potassium replacement NDC.
5. Invoke `follow_up_lab_ordering` with `code=K` and `date=2023-11-14T08:00:00+00:00`.
6. `FINISH(["potassium replacement ordered", "follow‑up potassium test scheduled for 2023‑11‑14T08:00:00+00:00"])`.

**Incorrect output example:** `FINISH(["no replacement ordered"])` – the lab value was never evaluated.

## Success Indicators
- The agent extracts a numeric `valueQuantity.value` before deciding.
- The comparison uses the correct threshold and unit conversion.
- A `POST` to `/ServiceRequest` is made only when the condition is met.
- When a follow‑up is required, a second POST (or a call to `follow_up_lab_ordering`) occurs.
- The final `FINISH` array contains explicit statements about the actions taken.

## Failure Indicators
- The agent calls `FINISH` without a preceding value extraction step.
- The agent posts a replacement order regardless of the lab value.
- The `FINISH` output contains a generic message like `"no replacement ordered"` when the lab was low.
- No follow‑up order appears even though the task requested one.
- The extracted value is a string with units (e.g., `"3.5 mmol/L"`) and the comparison fails silently.
