---
description: "Require a lab Observation check before creating a MedicationRequest\
  \ that depends on the result. **Applicability Guard:** This skill is only triggered\
  \ when the task description explicitly contains a conditional medication order based\
  \ on a lab value (e.g., contains phrases like \"if [lab] is low/high/abnormal then\
  \ order\", mentions a specific lab code, and includes a medication or dosing instruction).\
  \ It will not be applied to generic queries such as retrieving patient age or other\
  \ non\u2011conditional tasks."
name: ensure_observation_condition_before_medication_order
provenance:
  action: ADD
  epoch: 3
  fixes: 5
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task2_28
  - task2_30
  - task2_6
  - task2_1
  - task2_26
  - task9_3
  update_cycle: 1
tags: []
version: 1
---

# ensure_observation_condition_before_medication_order

## Pattern Description
You must verify the numeric result of a relevant Observation before you place a MedicationRequest that is conditional on that result (e.g., “if potassium is low, order replacement”). The skill isolates the reusable pattern of extracting a lab value, applying a clinical threshold, and only proceeding with the order when the condition is satisfied. This prevents blind ordering and ensures the agent respects the clinical decision logic embedded in the instruction.

## When to Use This Skill
- The task **explicitly** says *"if [lab] is low/high/abnormal, then order …"*.
- The instruction mentions a specific lab code (e.g., `code=K` for potassium, `code=MG` for magnesium, `code=A1C` for HbA1c) **and** a medication/dosing action that depends on that lab value.
- The task also asks to schedule a follow‑up Observation (e.g., a repeat potassium draw the next day).

*Do not apply this skill to generic queries that do not involve a conditional medication order (e.g., “What is the patient’s age?”).*

## Common Failure Patterns
- Creating a `MedicationRequest` without first extracting the Observation value.
- Using the raw Observation bundle instead of the numeric `valueQuantity.value` (or parsed `valueString`).
- Ordering medication regardless of the threshold check, even when the lab is normal or missing.
- Forgetting to pair the medication order with the required follow‑up `ServiceRequest`.

## Recommended Patterns
**Pattern 1: Extract and evaluate the lab value**
1. After the required `GET /Observation?...` locate the most recent entry.
2. Extract the numeric result:
   - Preferred: `entry[0].resource.valueQuantity.value` (number).
   - If the lab is stored as a string, parse the number from `valueString`.
3. Compare against the clinical threshold defined in the instruction (e.g., potassium < 3.5 mmol/L is low).

**Pattern 2: Conditional order creation**
- **If the condition is met** → proceed to create the `MedicationRequest` (or other order).
- **If the condition is not met** → do **not** POST a `MedicationRequest`; simply `FINISH([])` or return a short answer.
- **If the Observation is missing** → also skip the order and finish.

**Pattern 3: Pairing with a follow‑up ServiceRequest**
When the instruction includes a follow‑up test:
1. Build a `ServiceRequest` with the appropriate LOINC code and `occurrenceDateTime` (e.g., tomorrow at 08:00).
2. POST the `ServiceRequest` **only after** the medication order has been approved by Pattern 2.

## Example Application
**Task:** "Check patient S6550627's most recent potassium level. If low, then order replacement potassium 40 mEq oral. Also schedule a serum potassium draw tomorrow at 08:00."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=Patient/S6550627`
2. From the returned Bundle, read `valueQuantity.value` → e.g., `3.2`.
3. Compare: `3.2 < 3.5` → condition true.
4. `POST http://localhost:8080/fhir/MedicationRequest` with the correct NDC and dosage.
5. `POST http://localhost:8080/fhir/ServiceRequest` for the repeat potassium draw (`code=K`, `occurrenceDateTime=2023-11-14T08:00:00+00:00`).
6. `FINISH([])`.

**If the value had been 4.0** the agent would skip steps 4‑5 and simply `FINISH([])`.

## Success Indicators
- The agent extracts a numeric value from the Observation before any order.
- A `MedicationRequest` is only posted when the extracted value satisfies the condition.
- When a follow‑up test is required, a `ServiceRequest` is posted **after** the medication order and with the correct timing.
- The final output is `FINISH([])` (or a short answer) with no stray orders.

## Failure Indicators
- `MedicationRequest` appears in the log without a preceding value extraction step.
- The agent posts a `MedicationRequest` even when the extracted value is above the threshold or when the Observation bundle is empty.
- The follow‑up `ServiceRequest` is posted without first confirming the condition.
- The agent includes the raw Observation bundle in the output instead of the numeric value.

## Guard Clause (Implementation Hint)
When parsing the task description, check for any of the following patterns before activating this skill:
- Regex `/\bif\b.*\b(low|high|abnormal)\b.*\border\b/i`
- Presence of a lab code (`code=`) **and** a medication keyword (`medication`, `prescribe`, `order`, `dose`).
If none are found, skip this skill and let the default execution proceed.
