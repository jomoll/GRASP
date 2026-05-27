---
description: "Decide on potassium replacement and schedule a follow\u2011up test when\
  \ a potassium Observation is retrieved"
name: potassium_threshold_decision
provenance:
  action: ADD
  epoch: 3
  fixes: 4
  probe_score: 1
  regressions: 3
  triggering_sample_ids:
  - task9_1
  - task8_5
  - task5_19
  - task10_24
  - task9_5
  - task9_11
  - task10_20
  - task10_13
  - task10_17
  - task10_27
  update_cycle: 0
tags:
- electrolyte
- decision
- potassium
version: 1
---

# Potassium Threshold Decision and Replacement Ordering

## Pattern Description
You must treat every potassium (`code=K`) Observation as a decision point. Extract the numeric value in **mmol/L** from `valueQuantity.value`. If the value is **≤ 3.5 mmol/L**, automatically create a replacement **ServiceRequest** (using the NDC supplied in the task context) and also schedule a follow‑up serum potassium Observation for the next day at 08:00. If the value is above the threshold, simply report the level and do **not** create any orders.

## When to Use This Skill
- After a `GET .../Observation?code=K&patient=...` returns a non‑empty bundle and the task description mentions “low potassium”, “replacement”, or “order replacement”.
- When the task also asks to “pair this order with a morning serum potassium level to be completed the next day at 8am”.

## Common Failure Patterns
- Extracting the whole `valueQuantity` object or the `valueQuantity.unit` string instead of the numeric `value`.
- Comparing the value to the wrong threshold (e.g., 4.0 mmol/L) or using `>=` instead of `<=`.
- Omitting the ServiceRequest creation entirely when the level is low.
- Forgetting to schedule the follow‑up Observation (no second ServiceRequest or missing `occurrenceDateTime`).
- Returning free‑text sentences in `FINISH` instead of the required list format.

## Recommended Patterns
**Pattern 1: Core decision logic**
1. Locate the most recent entry in the Observation bundle (use `entry[0].resource`).
2. Read `valueQuantity.value` as a number → `potassium_val`.
3. If `potassium_val <= 3.5`:
   - **POST** a `ServiceRequest` for potassium replacement:
     ```json
     {
       "resourceType": "ServiceRequest",
       "status": "active",
       "intent": "order",
       "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "<NDC_FROM_CONTEXT>", "display": "Potassium replacement" }] },
       "subject": { "reference": "Patient/<MRN>" },
       "authoredOn": "<CURRENT_TIME>",
       "note": [{ "text": "Replace potassium per dosing instructions" }]
     }
     ```
   - **POST** a second `ServiceRequest` (or a `ProcedureRequest`) to schedule a serum potassium draw:
     ```json
     {
       "resourceType": "ServiceRequest",
       "status": "active",
       "intent": "order",
       "code": { "coding": [{ "system": "http://loinc.org", "code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma" }] },
       "subject": { "reference": "Patient/<MRN>" },
       "occurrenceDateTime": "<CURRENT_DATE+1day>T08:00:00+00:00",
       "authoredOn": "<CURRENT_TIME>"
     }
     ```
   - **FINISH** with a list containing the numeric value, e.g. `FINISH([3.2])`.
4. Else (value > 3.5):
   - **FINISH** with a list containing the numeric value, e.g. `FINISH([4.5])`.

**Pattern 2: Fallback / verification**
- If the Observation bundle is empty or missing `valueQuantity`, treat it as “no recent potassium level” and **FINISH([])** without ordering.
- Verify that the posted ServiceRequest returns a 201 status; if not, log a warning and still report the level.

**Pattern 3: Output formatting**
- Always return a JSON list with the numeric value only. Do **not** embed explanatory text.
- Example of correct output: `FINISH([3.2])`
- Example of wrong output: `FINISH(["Potassium is 3.2 mmol/L, low, ordering replacement."])`

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217`
2. From the returned bundle, extract `entry[0].resource.valueQuantity.value` → `potassium_val = 3.2`.
3. Since `3.2 <= 3.5`:
   - POST the replacement ServiceRequest (using the NDC supplied in the task context).
   - POST the follow‑up draw ServiceRequest with `occurrenceDateTime` set to tomorrow at 08:00.
4. `FINISH([3.2])`

## Success Indicators
- A ServiceRequest with the correct NDC code appears in the FHIR server.
- A second ServiceRequest with `occurrenceDateTime` = tomorrow 08:00 is present.
- The final agent output is exactly `FINISH([<numeric_value>])`.

## Failure Indicators
- No ServiceRequest is posted when `potassium_val <= 3.5`.
- The posted ServiceRequest uses the wrong code system or omits the NDC.
- The FINISH output contains free‑text or extra elements.
- The follow‑up draw is not scheduled (missing `occurrenceDateTime`).
