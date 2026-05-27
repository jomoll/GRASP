---
description: Add date filtering, numeric extraction, unit conversion and conditional
  ordering for lab observations
name: ensure_patient_lookup_before_observation_query
provenance:
  action: MODIFY
  epoch: 2
  fixes: 4
  parent_version: 1
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - task4_28
  - task9_1
  - task4_10
  - task9_9
  - task5_16
  - task9_5
  - task9_27
  - task2_17
  - task9_22
  - task9_8
  update_cycle: 1
tags:
- observation
- value_extraction
- date_filter
- conditional_order
version: 2
---

# ensure_patient_lookup_before_observation_query

## Pattern Description
You must always resolve a patient ID before querying any Observation. In addition, when a task mentions a time window (e.g., "within last 24 hours") you must apply a date filter to the Observation search. After retrieving the bundle, extract the numeric result from `valueQuantity.value` (or from a parsable `valueString`) and, if necessary, convert the units to the required output unit (e.g., mg/dL for magnesium). Finally, if the task includes a conditional order (e.g., "if low, then order replacement"), compare the extracted value against the clinical threshold and issue the appropriate ServiceRequest before finishing.

## When to Use This Skill
- When a task asks for the most recent lab value (magnesium, potassium, HbA1c, etc.)
- When the task specifies a time constraint such as "within last 24 hours"
- When the answer must be a plain number (or -1) rather than a descriptive string
- When the task includes a conditional order based on the lab result (e.g., low potassium → order replacement)

## Common Failure Patterns
- Omitting the `date` filter, causing the agent to consider stale observations
- Extracting the whole `valueQuantity` object or concatenating the unit (e.g., `"2.2 mg/dL"`)
- Returning a string or array instead of a single numeric value
- Failing to issue the replacement order when the value is below the threshold
- Using the wrong field (`valueString` when `valueQuantity` is present) leading to parsing errors

## Recommended Patterns
**Pattern 1: Patient lookup and Observation query with optional date filter**
1. `GET http://localhost:8080/fhir/Patient?identifier={MRN}` → obtain `Patient/{id}`
2. Build the Observation query:
   - Base: `GET http://localhost:8080/fhir/Observation?code={CODE}&patient=Patient/{id}`
   - If the task mentions a time window, add `date=ge{START}` and optionally `date=le{END}` where `{START}` = current time minus window (ISO‑8601).
   - Example for last 24 h: `date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`

**Pattern 2: Numeric value extraction and unit normalization**
1. From the returned Bundle, locate the entry with the latest `effectiveDateTime`.
2. Prefer `valueQuantity.value` (numeric). If only `valueString` exists, parse the leading number.
3. If the unit is not the required one, apply a conversion (e.g., mmol/L → mg/dL for magnesium: multiply by 2.0).
4. If no observation in the window, set result to `-1`.

**Pattern 3: Conditional ordering based on thresholds**
1. Define clinical thresholds (example: magnesium < 1.7 mg/dL, potassium < 3.5 mmol/L).
2. After extraction, compare the numeric value to the threshold.
3. If below, issue a `POST` ServiceRequest with the appropriate NDC or LOINC code.
4. Include a clear note indicating the reason for the order.

**Pattern 4: Final output formatting**
- For pure value requests: `FINISH([<number>])` or `FINISH([-1])`.
- For value‑plus‑date requests: `FINISH([<number>, "<ISO‑date>"])`.
- Never wrap the number in quotes or include explanatory text.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S3213957 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S3213957` → obtain `Patient/S3213957`.
2. `GET http://localhost:8080/fhir/Observation?code=MG&patient=Patient/S3213957&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`.
3. From the bundle, pick the entry with the greatest `effectiveDateTime`.
4. Extract `valueQuantity.value` (e.g., `1.8`). If the unit is `mmol/L`, convert: `1.8 * 2.0 = 3.6 mg/dL`.
5. No conditional order required, so output: `FINISH([3.6])`.

**Task with conditional order:** "Check patient S0581164's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium."
1‑4. Same as above, resulting in `value = 1.5 mg/dL`.
5. Since `1.5 < 1.7`, issue:
```json
POST http://localhost:8080/fhir/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "NDC_FOR_MG", "display": "IV Magnesium" }] },
  "subject": { "reference": "Patient/S0581164" },
  "status": "active",
  "intent": "order",
  "authoredOn": "2023-11-13T10:15:00+00:00",
  "note": { "text": "Ordered due to low magnesium (1.5 mg/dL)." }
}
```
6. Finish with the value: `FINISH([1.5])`.

## Success Indicators
- The agent always performs a Patient GET before any Observation GET.
- Observation GET URLs contain `date=ge...` when a time window is mentioned.
- The final FINISH output is a numeric array (or number‑plus‑date) with no extra text.
- When a low value is detected, a ServiceRequest POST is issued before FINISH.

## Failure Indicators
- Missing `date` parameters in the Observation request despite a time‑window cue.
- FINISH output contains strings, arrays of strings, or explanatory sentences.
- No ServiceRequest is posted when the task explicitly requires ordering on low value.
- The extracted value includes the unit (e.g., `"2.2 mg/dL"`).
