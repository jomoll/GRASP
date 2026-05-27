---
description: Correctly interpret lab thresholds and order follow-up labs when replacement
  is needed or when task explicitly requires follow-up
name: lab_value_threshold_interpretation_and_conditional_ordering
provenance:
  action: MODIFY
  epoch: 4
  fixes: 2
  parent_version: 2
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task9_9
  - task5_16
  - task9_27
  - task5_19
  - task10_24
  - task3_14
  - task3_17
  - task9_14
  - task10_21
  - task10_20
  update_cycle: 0
tags: []
version: 3
---

# Lab Value Threshold Interpretation and Conditional Ordering

## Pattern Description

This skill governs how to interpret lab observation values against clinical thresholds and take conditional actions such as ordering replacement therapy or follow-up lab tests. The core capability is: retrieve the most recent lab value, evaluate it against the specified threshold, and execute the appropriate action (order replacement, order follow-up lab, or do nothing).

When a task says "If low, then order replacement" or "If the lab value result date is greater than 1 year old, order a new lab test", you must first retrieve the lab, then evaluate the condition, then act. The action must match exactly what the task specifies — do not add extra actions not requested.

## When to Use This Skill

- When a task asks to check a lab value and conditionally order replacement therapy (e.g., "If low, order replacement IV magnesium")
- When a task asks to check a lab value and conditionally order a follow-up lab (e.g., "If the lab value result date is greater than 1 year old, order a new HbA1C lab test")
- When a task asks to check a lab value and conditionally do nothing (e.g., "If no magnesium level has been recorded in the last 24 hours, don't order anything")
- When a task asks for a lab value and specifies a fallback value like -1 if not available

## Common Failure Patterns

- Returning `[-1]` when a task asks to conditionally order a follow-up lab and no lab is found — instead, you should order the follow-up lab since the condition (no recent lab) is effectively met
- Ordering replacement therapy when the task only asked for a follow-up lab, or vice versa
- Ordering a follow-up lab when the task explicitly says "don't order anything" if no lab is found
- Extracting `valueQuantity.value` but including units in the output when the task expects a bare number
- Using the wrong threshold value (e.g., using 1.8 mg/dL for magnesium when the task specifies a different threshold)
- Failing to include the `date` parameter in the GET request when the task specifies a time window (e.g., "within last 24 hours")

## Recommended Patterns

**Pattern 1: Retrieve the lab value with correct parameters**
1. Identify the lab code from the task (e.g., "MG" for magnesium, "A1C" for HbA1C, "K" for potassium)
2. If the task specifies a time window (e.g., "within last 24 hours"), add the `date` parameter with the appropriate `ge` (greater than or equal) value
3. Issue GET to `/Observation?code={code}&patient={patientId}` with optional `&date=ge{timestamp}`
4. Check `total` in the response bundle — if 0, handle according to task instructions

**Pattern 2: Handle the "no lab found" case correctly based on task type**
- If the task says "If no lab has been recorded, don't order anything" → FINISH with a message like "No [lab name] level has been recorded in the last [time period]. No replacement ordered."
- If the task says "If the lab value result date is greater than 1 year old, order a new lab test" AND no lab is found → the condition is effectively met (no recent lab), so order the new lab test using the LOINC code provided in the task
- If the task says "The answer should be -1 if a measurement is not available" → FINISH with `[-1]`
- If the task asks for both the value and a conditional action, and no lab is found → follow the conditional action logic (e.g., order the new lab since no recent lab exists)

**Pattern 3: Extract the value correctly**
1. Sort entries by `effectiveDateTime` descending to get the most recent
2. Extract `valueQuantity.value` as a bare number — do NOT include units
3. If the value is in different units than expected, convert if possible, otherwise use as-is

CORRECT: `valueQuantity.value` extracted as `1.8`
WRONG:   `valueQuantity.value` concatenated with `valueQuantity.unit` as `"1.8 mg/dL"`

**Pattern 4: Evaluate threshold and take action**
1. Compare the extracted value against the threshold specified in the task
2. If the condition is met (e.g., value < threshold), take the specified action:
   - For replacement: POST a MedicationRequest with the correct NDC code, dose, and route
   - For follow-up lab: POST an Observation or ServiceRequest with the correct LOINC code
3. If the condition is not met, FINISH with a message indicating no action needed

## Example Application

**Task:** "What's the last HbA1C (hemoglobin A1C) value in the chart for patient S0789363 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step-by-step:**

1. Issue GET to `/Observation?code=A1C&patient=S0789363`
2. Check `total` in response — if 0, the condition "no recent lab" is effectively met, so order the new lab test
3. To order the new lab, POST to `/Observation` with:
   - `code.coding[0].code` = "4548-4" (the LOINC code for HbA1C)
   - `subject.reference` = "Patient/S0789363"
   - `status` = "final"
   - `effectiveDateTime` = current time
   - `valueString` or appropriate value field (this is an order, not a result)
4. FINISH with confirmation message

CORRECT output when no lab found: `FINISH(["Ordered new HbA1C lab test for patient S0789363 because no recent result was found."])`
WRONG output when no lab found: `FINISH([-1])`

**Task:** "Check patient S2402518's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step-by-step:**

1. Issue GET to `/Observation?code=MG&patient=S2402518&date=ge2023-11-12T10:15:00Z`
2. Check `total` in response — if 0, FINISH with "No magnesium level has been recorded in the last 24 hours. No replacement ordered."
3. If results exist, sort by `effectiveDateTime` descending, extract `valueQuantity.value`
4. Compare against threshold (typically < 1.8 mg/dL for low magnesium)
5. If low, POST MedicationRequest with NDC for IV magnesium, appropriate dose, and route
6. If not low, FINISH with message indicating no action needed

## Success Indicators

- When no lab is found and task says "don't order anything", agent returns a descriptive message instead of `[-1]`
- When no lab is found and task says to conditionally order a follow-up lab, agent orders the lab instead of returning `[-1]`
- When lab is found and condition is met, agent takes the correct action (replacement or follow-up lab)
- When lab is found and condition is not met, agent returns a message indicating no action needed
- Value is extracted as a bare number without units

## Failure Indicators

- Returning `[-1]` when the task expects a conditional action on missing data
- Ordering replacement when the task only asked for a follow-up lab
- Ordering a follow-up lab when the task explicitly says not to order anything
- Including units in the value output when the task expects a bare number
- Using the wrong threshold value
- Missing the `date` parameter when a time window is specified
