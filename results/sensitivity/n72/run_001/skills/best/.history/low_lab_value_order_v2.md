---
description: "Add explicit intent check before creating ServiceRequest or MedicationRequest\
  \ for low\u2011value labs"
name: low_lab_value_order
provenance:
  action: MODIFY
  epoch: 2
  fixes: 6
  parent_version: 1
  probe_score: 2
  regressions: 6
  triggering_sample_ids:
  - task10_20
  - task8_13
  - task9_14
  - task2_28
  - task9_3
  - task10_21
  - task9_5
  - task4_28
  - task1_6
  - task2_22
  update_cycle: 0
tags: []
version: 2
---

# Low Lab Value Order with Explicit Intent Check

## Pattern Description
You must only place orders (ServiceRequest or MedicationRequest) when the clinical task **explicitly** asks for an order and the laboratory value meets the trigger condition. First, parse the natural‑language task description for clear ordering intent (e.g., "order", "request", "prescribe", "schedule a repeat test"). Then evaluate the lab value against the low‑value threshold. If either the intent is missing or the value does not satisfy the trigger, **do not** issue any POST request.

## When to Use This Skill
- When a task asks to *check* a lab value and *conditionally* order a medication or repeat test.
- When the task includes a time‑based rule (e.g., "if result is >1 year old, order a new test").
- When the task mentions a follow‑up lab **as part of the same instruction** (e.g., "pair this order with a morning serum potassium level").
- Any situation where the agent is about to POST a `ServiceRequest` or `MedicationRequest`.

## Common Failure Patterns
- Posting a `ServiceRequest` for a repeat HbA1c even though the task only required reporting the value.
- Creating an extra follow‑up `ServiceRequest` for a lab that was not explicitly requested.
- Issuing an order when the lab value is within normal range but the task only asked for the value.
- Missing the keyword check and assuming an order is always needed.

## Recommended Patterns
**Pattern 1: Detect explicit ordering intent**
1. Scan the task description for any of the trigger words: `order`, `request`, `prescribe`, `schedule`, `repeat`, `follow‑up`.
2. If none are found, set `order_intent = false` and skip any POST.
3. If found, set `order_intent = true`.

**Pattern 2: Evaluate lab value against threshold**
1. Extract the numeric value from the Observation (`valueQuantity.value`).
2. Compare to the task‑specified low‑value threshold (e.g., potassium < 3.5 mmol/L, magnesium < 1.5 mg/dL).
3. For date‑based rules, parse `effectiveDateTime` and compare to the current context time.
4. Only proceed if `order_intent && (value_below_threshold || date_rule_triggered)`.

**Pattern 3: Prevent duplicate or unnecessary ServiceRequests**
1. Before POSTing, search existing `ServiceRequest` resources for the same patient, code, and intent within a reasonable window (e.g., 24 h).
2. If a matching request already exists, skip creating a new one.

**Pattern 4: Build the correct POST body**
- For a repeat lab test:
  ```json
  {
    "resourceType": "ServiceRequest",
    "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC>", "display": "<Display>" }] },
    "authoredOn": "<CURRENT_TIME>",
    "status": "active",
    "intent": "order",
    "priority": "routine",
    "subject": { "reference": "Patient/<MRN>" },
    "note": [{ "text": "Ordered per task instruction" }]
  }
  ```
- For a medication replacement:
  ```json
  {
    "resourceType": "MedicationRequest",
    "medicationCodeableConcept": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "<NDC>", "display": "<Medication>" }] },
    "authoredOn": "<CURRENT_TIME>",
    "status": "active",
    "intent": "order",
    "subject": { "reference": "Patient/<MRN>" },
    "dosageInstruction": [{ "text": "<Dosage>" }]
  }
  ```

## Example Application
**Task:** "What’s the last HbA1C value for patient S0722219 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. Detect intent: the phrase "order a new HbA1C lab test" contains the keyword `order` → `order_intent = true`.
2. GET Observation `A1C` for patient S0722219.
3. Extract `effectiveDateTime` = `2022-03-08T08:14:00+00:00`.
4. Compare to current time `2023-11-13T10:15:00+00:00`; difference > 1 year → `date_rule_triggered = true`.
5. Since `order_intent && date_rule_triggered`, construct ServiceRequest POST as shown in Pattern 4.
6. FINISH with the numeric value and date.

**Correct output:**
```json
FINISH([6.5, "2022-03-08T08:14:00+00:00"])
```
**Wrong output (unnecessary order):**
```json
POST ServiceRequest …
FINISH([6.5, "2022-03-08T08:14:00+00:00"])
```

## Success Indicators
- No `POST http://.../ServiceRequest` or `MedicationRequest` appears unless the task description contains an ordering keyword.
- When an order is placed, the lab value truly meets the low‑value or date condition.
- Duplicate orders for the same patient/code within the same execution are avoided.

## Failure Indicators
- A `POST ServiceRequest` is sent even though the task description lacks any ordering language.
- An order is placed when the lab value is normal and no date rule applies.
- Multiple identical ServiceRequests are created for the same patient in one task run.
