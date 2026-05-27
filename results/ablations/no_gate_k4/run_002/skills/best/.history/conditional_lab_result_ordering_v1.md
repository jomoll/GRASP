---
description: Decide whether to place a replacement order based on a recent lab value
  and handle missing results
name: conditional_lab_result_ordering
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task8_29
  update_cycle: 1
tags: []
version: 1
---

# Conditional Lab Result Ordering

## Pattern Description
You must evaluate a recent laboratory Observation before deciding to create any follow‑up ServiceRequest or MedicationRequest. The skill extracts the numeric result from `Observation.valueQuantity.value`, compares it to a task‑specific low‑threshold, and only issues an order when the value is below that threshold. If the query returns no recent Observation, you must **not** place any order. This pattern applies to any lab‑driven conditional ordering (e.g., potassium, magnesium, HbA1c repeat).

## When to Use This Skill
- When a task says *"If low, then order replacement …"* or *"If the result is older than X, order a repeat test"*.
- When the task references a specific LOINC code (e.g., `K` for potassium, `MG` for magnesium, `A1C` for HbA1c) and provides a time window (e.g., last 24 h).
- When the task also asks to schedule a follow‑up lab (e.g., next‑day serum potassium).

## Common Failure Patterns
- Ordering replacement **without** checking the numeric value (agent simply posts a ServiceRequest).
- Using the wrong field (`valueString` or `effectiveDateTime`) for the numeric comparison.
- Treating the presence of any Observation as “low” even when the value is normal.
- Failing to handle the *no recent result* case and ordering anyway.
- Returning a list of values or a free‑text answer instead of a single structured decision.

## Recommended Patterns
**Pattern 1: Retrieve the recent Observation**
1. Build a GET request that filters by `code=<LOINC>` (or short code) **and** `patient=<MRN>`.
2. If a time window is required, add `date=ge<now-24h>` and `date=le<now>` parameters.
3. Inspect the response Bundle:
   - If `total == 0`, treat as *no recent result*.
   - Otherwise, locate the first entry’s `resource` → `valueQuantity`.
4. Extract:
   - `value = resource.valueQuantity.value` (numeric)
   - `unit = resource.valueQuantity.unit` (optional, for logging)
   - `resultDate = resource.effectiveDateTime`

**Pattern 2: Evaluate the threshold**
- Define the low‑threshold in the skill (e.g., potassium < 3.5 mmol/L, magnesium < 1.5 mg/dL, HbA1c age > 1 year).
- If `value < threshold` **AND** a recent result exists, proceed to ordering.
- If no recent result, **do not** order.
- For age‑based repeat tests, compare `resultDate` to `now` and order only if older than the allowed interval.

**Pattern 3: Create the appropriate order**
- **Replacement medication**: POST a `MedicationRequest` with the NDC code supplied in the task context.
- **Follow‑up lab**: POST a `ServiceRequest` with the same LOINC code, set `occurrenceDateTime` to the required future time (e.g., `now + 1 day` at 08:00).
- Include `subject.reference = "Patient/<MRN>"` and `authoredOn = now`.
- Add a `note.text` explaining the reason (e.g., "Low potassium, replacement ordered").

**Pattern 4: Finish with a concise answer**
- If an order was placed, return a single‑sentence string such as:
  `FINISH(["Potassium replacement ordered; follow‑up draw scheduled for 2023-11-14T08:00:00+00:00."])`
- If no order, return a single‑sentence explanation:
  `FINISH(["No recent potassium result; no replacement ordered."])`

## Example Application
**Task:** "Check patient S1796597's most recent potassium level. If low (<3.5 mmol/L), then order replacement potassium and schedule a morning serum potassium draw for the next day at 08:00."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1796597`
2. Parse the Bundle. Suppose the entry contains:
   ```json
   "valueQuantity": {"value": 3.2, "unit": "mmol/L"},
   "effectiveDateTime": "2023-11-12T09:00:00+00:00"
   ```
3. Compare `3.2 < 3.5` → true, so ordering is required.
4. POST MedicationRequest for potassium replacement (use NDC from task context).
5. POST ServiceRequest for follow‑up potassium:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": {"coding":[{"system":"http://loinc.org","code":"2823-3","display":"Serum potassium"}]},
     "authoredOn":"2023-11-13T10:15:00+00:00",
     "status":"active",
     "intent":"order",
     "priority":"stat",
     "subject":{"reference":"Patient/S1796597"},
     "occurrenceDateTime":"2023-11-14T08:00:00+00:00",
     "note":{"text":"Follow‑up after low potassium replacement"}
   }
   ```
6. `FINISH(["Potassium replacement ordered; follow‑up draw scheduled for 2023-11-14T08:00:00+00:00."])`

## Success Indicators
- The agent issues a GET for the correct Observation code and patient.
- The numeric value is extracted from `valueQuantity.value`.
- An order is only posted when the value is below the defined threshold **and** a recent result exists.
- The final FINISH output is a single string, not a list or free‑text paragraph.

## Failure Indicators
- The agent posts an order without performing the numeric comparison.
- The agent uses `valueString` or other non‑numeric fields for the threshold check.
- The agent orders when `total == 0` (no recent result).
- The FINISH output contains a JSON array of multiple items or includes the raw lab value text.
- The agent forgets to schedule the follow‑up ServiceRequest when required.
