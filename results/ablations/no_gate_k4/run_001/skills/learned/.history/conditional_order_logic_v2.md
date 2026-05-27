---
description: "Add low\u2011threshold mapping and order creation for potassium and\
  \ magnesium replacement."
name: conditional_order_logic
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task8_19
  - task9_22
  - task8_3
  - task8_21
  - task9_1
  - task9_5
  - task10_27
  - task8_7
  - task8_9
  - task1_20
  update_cycle: 1
tags:
- order_logic
- lab_threshold
version: 2
---

# conditional_order_logic

## Pattern Description
You must decide whether to place a replacement **ServiceRequest** based on a numeric lab result.  A reusable mapping of LOINC codes (or short codes) to low‑threshold values and the corresponding replacement medication NDC is maintained.  When the extracted value is below the threshold, you create a `ServiceRequest` for the replacement and optionally schedule a follow‑up observation as instructed.

## When to Use This Skill
- After extracting a numeric lab value from an `Observation` (e.g., potassium "K" or magnesium "MG").
- The task explicitly says *"If low, then order replacement …"*.
- The task may also request a paired follow‑up lab (e.g., next‑day potassium level).

## Common Failure Patterns
- No low‑threshold rule defined, so the agent never creates the order.
- Comparing the value as a string instead of a number.
- Using the wrong field (`valueString` instead of `valueQuantity.value`).
- Forgetting to include the NDC code supplied in the task context.

## Recommended Patterns
**Pattern 1: Threshold lookup and decision**
1. Identify the lab code from the task (`code` parameter in the GET URL).
2. Use the mapping table:
   ```json
   {
     "K": { "low": 3.5, "unit": "mmol/L", "ndc": "<K_NDC_FROM_CONTEXT>" },
     "MG": { "low": 1.6, "unit": "mg/dL", "ndc": "<MG_NDC_FROM_CONTEXT>" }
   }
   ```
3. Extract the numeric value from `valueQuantity.value` (already normalized by `numeric_lab_value_extraction`).
4. If `value < low` **AND** the task mentions ordering, proceed to Pattern 2.

**Pattern 2: Create replacement ServiceRequest**
```json
POST {api_base}/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "code": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "{{ndc}}" }] },
  "subject": { "reference": "Patient/{{patient_id}}" },
  "occurrenceTiming": { "repeat": { "frequency": 1, "period": 1, "periodUnit": "d" } }
}
```
If the task also asks for a next‑day lab, add a second `ServiceRequest` of type `Observation` with `code` set to the same lab and `occurrenceDateTime` set to *now + 1 day at 08:00*.

**Pattern 3: Final output**
- On success: `FINISH(["Replacement order placed for {{code}} (value {{value}} {{unit}}) and follow‑up scheduled."])`
- On no‑order needed: `FINISH(["No replacement needed; {{code}} value {{value}} {{unit}} is within normal range."])`

## Example Application
**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium … also pair this order with a morning serum potassium level tomorrow at 8 am."

**Step‑by‑step:**
1. GET `Observation?code=K&patient=S6474456` → bundle with latest entry.
2. Extract `valueQuantity.value = 3.4` (mmol/L).
3. Lookup mapping for `K`: low = 3.5, ndc = `12345‑6789‑01` (from task context).
4. Since 3.4 < 3.5, POST a `ServiceRequest` for the NDC.
5. POST a second `ServiceRequest` for a future potassium Observation with `occurrenceDateTime = 2023‑11‑14T08:00:00+00:00`.
6. FINISH(["Replacement order placed for K (value 3.4 mmol/L) and follow‑up scheduled."])

## Success Indicators
- A `POST /ServiceRequest` is issued with the correct NDC code.
- A second `POST /ServiceRequest` (or `Observation`) is issued when a follow‑up is required.
- FINISH output contains the confirmation string, not just the raw lab value.

## Failure Indicators
- No `POST` is made despite the lab value being below the threshold.
- The `POST` body contains the wrong NDC or missing `subject` reference.
- FINISH returns only the lab value (e.g., `FINISH(["3.4 mmol/L"])`).
