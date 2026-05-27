---
description: Extend to enforce structured FINISH output with value, date, and clinical
  recommendation, and trigger orders when needed
name: observation_value_extraction_and_recency_check
provenance:
  action: MODIFY
  epoch: 0
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  - task5_16
  update_cycle: 1
tags: []
version: 2
---

# observation_value_extraction_and_recency_check

## Pattern Description
You must extract the most recent Observation for a given LOINC or code, evaluate its recency and clinical range, and then produce a **single FINISH response** that includes the numeric value, the timestamp of that observation, and a clear clinical recommendation (e.g., "no replacement ordered", "order replacement", or "order repeat test"). If the observation is older than the allowed interval or indicates a low value, you must also issue the appropriate FHIR POST request **before** finishing.

## When to Use This Skill
- When a task asks for the latest lab value (e.g., potassium, magnesium, HbA1c) and a follow‑up action based on that value.
- When the instruction requires a decision such as ordering medication, ordering a repeat lab, or stating that no action is needed.
- When the answer must be a plain‑text summary, not a JSON array or raw number.

## Common Failure Patterns
- FINISH returns only the raw value (`FINISH(["3.9 mmol/L"])`).
- FINISH omits the observation date (`FINISH(["Potassium 3.9 mmol/L"])`).
- FINISH does not mention the clinical decision (`FINISH(["Potassium 3.9 mmol/L"])`).
- Required order (MedicationRequest or ServiceRequest) is not created when the value is low or outdated.
- The agent posts the order but still finishes with a generic success message that does not echo the order details.

## Recommended Patterns
**Pattern 1: Extract latest observation**
1. Issue a GET to `/Observation?code={code}&patient={MRN}` (add optional `date` filters if the task limits the window).
2. From the returned Bundle, locate the entry with the highest `effectiveDateTime`.
3. Read `valueQuantity.value` (or `valueString` for non‑numeric) and `effectiveDateTime`.
4. Convert units if needed (use `include_units_in_output`).

**Pattern 2: Decision logic**
- Define the clinical threshold for the test (e.g., potassium < 3.5 mmol/L, magnesium < 1.5 mg/dL, HbA1c older than 1 year).
- If the value is out of range **or** the observation date is older than the allowed interval, prepare the appropriate POST request:
  - MedicationRequest for replacement therapy.
  - ServiceRequest for a repeat lab.
- Record the POST request details (code, dosage, timing) before proceeding.

**Pattern 3: Structured FINISH output**
- Always format the final answer as a single plain‑text sentence:
  - `FINISH(["{Test} = {value}{unit} recorded on {date}. {Recommendation}."])`
- Example (low potassium, order placed):
  - `FINISH(["Potassium = 3.1 mmol/L recorded on 2023-11-12T08:00:00+00:00. Ordered 40 mEq oral potassium replacement and scheduled repeat test for 2023-11-14T08:00:00+00:00."])`
- Example (no action needed):
  - `FINISH(["Magnesium = 2.0 mg/dL recorded on 2023-11-12T13:31:00+00:00. No replacement ordered."])`

## Example Application
**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium ..."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S6474456`
2. Extract the newest entry: `valueQuantity.value = 3.1`, `unit = "mmol/L"`, `effectiveDateTime = "2023-11-12T08:00:00+00:00"`.
3. Threshold: low if `< 3.5`. Value is low → prepare order.
4. `POST http://localhost:8080/fhir/MedicationRequest` with NDC `40032-917-01`, dose `40 mEq`, route `oral`.
5. `POST http://localhost:8080/fhir/ServiceRequest` for repeat potassium test at `2023-11-14T08:00:00+00:00`.
6. `FINISH(["Potassium = 3.1 mmol/L recorded on 2023-11-12T08:00:00+00:00. Ordered 40 mEq oral potassium replacement and scheduled repeat test for 2023-11-14T08:00:00+00:00."])`

## Success Indicators
- FINISH output contains **value**, **date**, and a **clear recommendation**.
- Any required POST request appears in the trace **before** the FINISH call.
- The wording matches the pattern (no JSON arrays, no extra explanatory text).

## Failure Indicators
- FINISH returns only a number or an array.
- The observation date is missing or incorrectly formatted.
- No POST request is made when the decision logic dictates an order.
- The FINISH sentence does not mention the clinical action taken.
