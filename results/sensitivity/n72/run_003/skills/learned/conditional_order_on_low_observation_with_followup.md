---
description: "Order replacement medication and schedule a follow\u2011up lab when\
  \ a lab value is below its low threshold"
name: conditional_order_on_low_observation_with_followup
provenance:
  action: ADD
  epoch: 2
  fixes: 8
  probe_score: 1
  regressions: 2
  triggering_sample_ids: []
  update_cycle: 1
tags: []
version: 1
---

# Conditional Order on Low Observation with Follow‑up Lab

## Pattern Description
You must handle tasks that ask you to check a recent lab or vital‑sign Observation and, **if the value is below the low threshold**, create two separate `ServiceRequest` resources:
1. a replacement medication order (using the NDC or other code supplied in the task context), and
2. a follow‑up laboratory order scheduled for the next day at a specific time (often 08:00).
This pattern is reusable for any analyte (potassium, magnesium, etc.) where the clinician wants a replacement and a repeat test.

## When to Use This Skill
- The instruction contains “If low, then order replacement …” **and** a phrase about “pair this order with a … lab to be completed the next day at 8am” (or any explicit future time).
- The task provides the observation code (e.g., `K` for potassium) and the replacement medication NDC or SNOMED code.
- The task may also give the low‑threshold numeric value or expect you to use the reference range from the Observation.

## Common Failure Patterns
- Agent only performs a `GET` for the Observation and finishes without creating any orders.
- Agent extracts the value but compares it to the wrong field (e.g., `effectiveDateTime` instead of `valueQuantity.value`).
- Replacement order is posted but the follow‑up lab is omitted or scheduled at the wrong datetime.
- The follow‑up `ServiceRequest` uses the wrong `code` (e.g., medication code instead of lab LOINC).

## Recommended Patterns
**Pattern 1: Retrieve and evaluate the Observation**
1. `GET {api_base}/Observation?code={CODE}&patient={MRN}`
2. From the first entry in the Bundle, read `valueQuantity.value` (numeric) **or** parse `valueString` if only a string is present.
3. Compare the numeric value to the low threshold supplied in the task (or to the `referenceRange.low` if present).
4. If the value is **≥ low**, finish with no further action.

**Pattern 2: Create replacement medication order**
1. Build a `ServiceRequest` with:
   - `resourceType: "ServiceRequest"`
   - `code.coding[0].system` set to the system of the replacement (e.g., `http://hl7.org/fhir/sid/ndc`).
   - `code.coding[0].code` set to the NDC provided.
   - `authoredOn` = current task time.
   - `status: "active"`, `intent: "order"`, `priority: "stat"` (or as instructed).
   - `subject.reference` = `"Patient/{MRN}"`.
   - Optional `note.text` describing the indication.
2. `POST {api_base}/ServiceRequest` with the JSON body.

**Pattern 3: Schedule follow‑up lab**
1. Compute `followUpDateTime = now + 1 day` and set the time component to `08:00` (or the time given in the task).
2. Build a second `ServiceRequest` with:
   - `code.coding[0].system = "http://loinc.org"`
   - `code.coding[0].code` = the LOINC code for the required lab (e.g., `2823-3` for serum potassium).
   - `authoredOn = now`
   - `occurrenceDateTime = followUpDateTime`
   - `status: "active"`, `intent: "order"`, `priority: "routine"` (or as instructed).
   - `subject.reference = "Patient/{MRN}"`.
   - `note.text = "Follow‑up lab as instructed after low result."
3. `POST {api_base}/ServiceRequest` with this body.

**Pattern 4: Finish**
- After both POSTs succeed, call `FINISH([])` (or return any required confirmation).

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium (NDC 12345‑6789‑01) and pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217`
2. Extract `valueQuantity.value = 3.2` (mmol/L). Low threshold = 3.5 mmol/L (provided in task).
3. Since 3.2 < 3.5, proceed.
4. Build replacement order:
```json
{
  "resourceType": "ServiceRequest",
  "code": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "12345-6789-01", "display": "Potassium chloride" }] },
  "authoredOn": "2023-11-13T10:15:00+00:00",
  "status": "active",
  "intent": "order",
  "priority": "stat",
  "subject": { "reference": "Patient/S3241217" },
  "note": { "text": "Replacement potassium ordered due to low result." }
}
```
5. `POST http://localhost:8080/fhir/ServiceRequest` with above body.
6. Compute follow‑up datetime = `2023-11-14T08:00:00+00:00`.
7. Build follow‑up lab order:
```json
{
  "resourceType": "ServiceRequest",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma" }] },
  "authoredOn": "2023-11-13T10:15:00+00:00",
  "occurrenceDateTime": "2023-11-14T08:00:00+00:00",
  "status": "active",
  "intent": "order",
  "priority": "routine",
  "subject": { "reference": "Patient/S3241217" },
  "note": { "text": "Follow‑up potassium level as instructed." }
}
```
8. `POST http://localhost:8080/fhir/ServiceRequest` with the follow‑up body.
9. `FINISH([])`

**CORRECT output:** Two successful `POST` calls followed by `FINISH([])`.
**WRONG output:** Only the `GET` call, or missing the follow‑up `ServiceRequest`.

## Success Indicators
- The agent issues a `POST` to `/ServiceRequest` for the replacement medication **and** another `POST` for the follow‑up lab.
- The `occurrenceDateTime` of the follow‑up request matches the required next‑day 08:00 time.
- The final `FINISH` call is reached after both POSTs succeed.

## Failure Indicators
- The agent finishes after the `GET` without any `POST`.
- Only one of the two required `ServiceRequest` resources is posted.
- The follow‑up request uses the wrong `code` or an incorrect datetime.
- The replacement order uses an incorrect NDC or omits the `subject` reference.
