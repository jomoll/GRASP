---
description: "Trigger replacement medication order and schedule follow\u2011up lab\
  \ when a lab value is below its low threshold"
name: conditional_order_on_low_observation
provenance:
  action: ADD
  epoch: 1
  fixes: 31
  probe_score: 11
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task10_17
  - task8_29
  - task2_17
  - task4_28
  - task2_28
  - task8_19
  - task10_27
  - task1_7
  - task8_21
  update_cycle: 0
tags: []
version: 1
---

# Conditional Order on Low Observation

## Pattern Description
You must use this skill whenever a task asks you to check a recent lab Observation and, **if the value is low**, place a replacement medication order and optionally schedule a follow‑up lab. The skill first extracts the numeric value from the most recent Observation (using `valueQuantity.value` or parsing `valueString`). It then compares the value against a low‑threshold that is either supplied in the task context or known from clinical guidelines. If the value is below the threshold, you construct one or more `ServiceRequest` resources: one for the replacement medication (using the NDC or medication code provided) and, if required, a second for a repeat lab (using the LOINC code and a specific future `occurrenceDateTime`). If the Observation is missing or not low, you simply finish without ordering.

## When to Use This Skill
- Task description contains phrases like "If low, then order replacement ..." or "pair this order with a ... level to be completed the next day".
- You have just performed a `GET` for an Observation (e.g., `GET .../Observation?code=K&patient=...`).
- The Observation bundle contains a numeric result (`valueQuantity.value`) or a parsable string (e.g., "3.9 mmol/L").
- The task provides either an explicit low‑threshold (e.g., `low_threshold=3.5`) or the clinical context implies a standard threshold (e.g., potassium <3.5 mmol/L, magnesium <1.5 mg/dL).

## Common Failure Patterns
- Agent extracts the value but **does not issue any POST** when the value is low (order_action_omitted).
- Agent finishes with the raw value (`FINISH([3.9])`) instead of creating a `ServiceRequest`.
- Agent creates an order but uses the wrong resource type or omits required fields (`code.coding`, `subject.reference`).
- Agent schedules a follow‑up lab but forgets to set `occurrenceDateTime` to the required future time.

## Recommended Patterns
**Pattern 1: Extract and evaluate the observation**
1. From the Observation bundle, locate the first entry with `resource.resourceType == "Observation"`.
2. Prefer `valueQuantity.value` as a number. If only `valueString` is present, parse the leading numeric token.
3. Compare the numeric value to the low threshold (provided in the task context or default).
   - CORRECT: `if value < low_threshold:`
   - WRONG: comparing the raw string or ignoring the threshold.

**Pattern 2: Issue replacement medication order when low**
1. Build a `ServiceRequest` JSON:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "<NDC_OR_MED_CODE>", "display": "Replacement <Substance>" }] },
     "authoredOn": "{{current_time}}",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/{{mrn}}" },
     "note": { "text": "Ordered because recent {{substance}} level was low ({{value}})." }
   }
   ```
2. POST to `/fhir/ServiceRequest`.
   - CORRECT: includes `code.coding`, `subject.reference`, and a clear `note`.
   - WRONG: omitting `code` or using an unrelated resource type.

**Pattern 3: Schedule follow‑up lab (optional)**
1. If the task requests a repeat measurement, create a second `ServiceRequest`:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC_CODE>", "display": "{{substance}} level" }] },
     "authoredOn": "{{current_time}}",
     "status": "active",
     "intent": "order",
     "priority": "routine",
     "subject": { "reference": "Patient/{{mrn}}" },
     "occurrenceDateTime": "{{next_day_08:00}}",
     "note": { "text": "Follow‑up {{substance}} level as per protocol." }
   }
   ```
2. POST this request after the medication order.
   - CORRECT: `occurrenceDateTime` set to the next calendar day at 08:00.
   - WRONG: missing `occurrenceDateTime` or using the current time.

## Example Application
**Task:** "Check patient S3228213's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3228213`
2. Extract the first Observation's `valueQuantity.value` → `3.2` mmol/L.
3. Compare to low threshold `3.5` mmol/L → value is low.
4. POST medication order:
   ```json
   { "resourceType":"ServiceRequest", "code":{"coding":[{"system":"http://www.nlm.nih.gov/research/umls","code":"<K_NDC>","display":"Potassium replacement"}]}, "authoredOn":"2023-11-13T10:15:00+00:00", "status":"active", "intent":"order", "priority":"stat", "subject":{"reference":"Patient/S3228213"}, "note":{"text":"Ordered because potassium was low (3.2 mmol/L)."} }
   ```
5. POST follow‑up lab order (next day 08:00):
   ```json
   { "resourceType":"ServiceRequest", "code":{"coding":[{"system":"http://loinc.org","code":"K","display":"Serum potassium"}]}, "authoredOn":"2023-11-13T10:15:00+00:00", "status":"active", "intent":"order", "priority":"routine", "subject":{"reference":"Patient/S3228213"}, "occurrenceDateTime":"2023-11-14T08:00:00+00:00", "note":{"text":"Follow‑up potassium level as per protocol."} }
   ```
6. `FINISH([])` (no direct numeric answer required).

## Success Indicators
- After the GET, the agent extracts a numeric value and stores it in a variable.
- The agent issues at least one `POST /fhir/ServiceRequest` when the value is below the threshold.
- The medication order includes the correct NDC/medication code and patient reference.
- If a follow‑up lab is required, a second ServiceRequest with `occurrenceDateTime` set to the next day at 08:00 is posted.
- The final `FINISH` call contains an empty array (or the placeholder answer) rather than the raw value.

## Failure Indicators
- The agent finishes with the raw observation value (`FINISH([3.2])`) and no POST.
- A POST is made but uses the wrong resource type (e.g., `MedicationRequest` instead of `ServiceRequest`).
- Required fields (`code.coding`, `subject.reference`) are missing or malformed.
- The follow‑up lab request lacks `occurrenceDateTime` or uses the current time instead of the scheduled time.
- The agent posts duplicate orders for the same low result.
