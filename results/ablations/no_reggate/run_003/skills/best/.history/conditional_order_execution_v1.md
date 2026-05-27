---
description: Detect and fulfill conditional order instructions based on lab values
name: conditional_order_execution
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 7
  regressions: 1
  triggering_sample_ids:
  - task8_15
  - task9_6
  - task9_9
  - task8_26
  - task5_19
  - task5_3
  - task1_20
  - task10_13
  - task9_1
  - task9_20
  update_cycle: 1
tags: []
version: 1
---

# Conditional Order Execution

## Pattern Description
You must recognize when a task contains a conditional order clause (e.g., "If low, then order replacement potassium") and automatically generate the appropriate `ServiceRequest` POST after evaluating the lab result. This skill bridges the gap between data retrieval and decision‑making, ensuring that orders are placed only when the clinical condition specified in the instruction is met.

## When to Use This Skill
- When a task asks to **check a lab value** and **order a medication or test** *only if* the value meets a threshold.
- When the instruction also requests a **follow‑up observation** (e.g., schedule a repeat potassium level).
- Example triggers:
  - "If low, then order replacement potassium..."
  - "If the result is > 140, order antihypertensive medication."
  - "If no measurement in last 24 h, do not order."

## Common Failure Patterns
- Agent returns only the lab value (`FINISH([value, date])`) without placing the required order.
- Agent places an order unconditionally, ignoring the conditional clause.
- Agent fails to schedule the paired follow‑up observation.
- Missing or incorrect `ServiceRequest` fields (e.g., wrong `code.coding.code`, missing `intent`).

## Recommended Patterns
**Pattern 1: Evaluate Conditional Clause**
1. Parse the instruction to identify the condition (e.g., "low" → value < lower_limit).
2. Extract the relevant numeric value from the Observation (`valueQuantity.value`).
3. Compare against the threshold defined in the instruction or a standard reference range.
4. If the condition is satisfied, proceed to Pattern 2; otherwise, finish with the lab result only.

**Pattern 2: Create ServiceRequest Order**
- Build a `ServiceRequest` JSON with:
  - `resourceType`: "ServiceRequest"
  - `code.coding[0].system`: appropriate code system (e.g., "http://www.nlm.nih.gov/research/umls" for NDC or "http://loinc.org" for labs)
  - `code.coding[0].code`: the NDC or LOINC code supplied in the task context.
  - `intent`: "order"
  - `status`: "active"
  - `authoredOn`: current task time.
  - `subject.reference`: `Patient/{MRN}`
  - Include any dosage instructions if provided.
- POST to `{api_base}/ServiceRequest`.

**Pattern 3: Schedule Follow‑up Observation (optional)**
- If the instruction requests a repeat lab, construct a `ServiceRequest` with `code` set to the lab LOINC and a `occurrenceTiming` or `occurrenceDateTime` for the desired future time (e.g., next day at 08:00).
- POST the follow‑up request after the primary order.

## Example Application
**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium (NDC 12345‑6789) and schedule a repeat potassium level tomorrow at 08:00."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S6474456`
2. Extract `valueQuantity.value` = 3.9 and `effectiveDateTime` = "2023-11-12".
3. Determine "low" threshold (e.g., < 3.5 mmol/L). 3.9 is *not* low → **no order**; `FINISH([3.9, "2023-11-12"])`.
4. If the value had been 3.2, create:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": {"coding":[{"system":"http://www.nlm.nih.gov/research/umls","code":"12345-6789"}]},
     "intent": "order",
     "status": "active",
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "subject": {"reference":"Patient/S6474456"}
   }
   ```
   POST to `/ServiceRequest`.
5. Then schedule follow‑up:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": {"coding":[{"system":"http://loinc.org","code":"2823-3"}]},
     "intent": "order",
     "status": "active",
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "occurrenceDateTime": "2023-11-14T08:00:00+00:00",
     "subject": {"reference":"Patient/S6474456"}
   }
   ```
   POST to `/ServiceRequest`.
6. Finally `FINISH([3.2, "2023-11-12"])`.

## Success Indicators
- A `ServiceRequest` POST is observed **only when** the lab value satisfies the conditional clause.
- Follow‑up `ServiceRequest` is posted when the task explicitly asks for a repeat lab.
- The final `FINISH` output contains the lab value and date, not the order details.

## Failure Indicators
- No `ServiceRequest` POST despite the condition being met.
- An order is posted when the condition is *not* met.
- Missing required fields in the posted `ServiceRequest` (e.g., no `code.coding[0].code`).
- Agent finishes with only the lab value while the instruction required an order.
