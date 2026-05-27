---
description: "Place a ServiceRequest when a retrieved lab value meets a low\u2011\
  threshold condition."
name: conditional_order_logic
provenance:
  action: ADD
  epoch: 1
  no_gate: true
  triggering_sample_ids:
  - task9_28
  - task10_20
  - task4_10
  - task5_17
  - task9_6
  - task4_27
  - task8_29
  - task5_7
  - task9_27
  - task9_14
  update_cycle: 0
tags:
- order
- conditional
- lab
version: 1
---

# Conditional Order Logic

## Pattern Description
You must decide whether to create a `ServiceRequest` (order) based on a lab Observation you have just retrieved. The pattern is reusable for any lab where the task specifies a *low‑threshold* (e.g., magnesium < 1.5 mg/dL, potassium < 3.5 mmol/L). First extract the numeric value and its unit, compare it to the threshold, and only if the condition is met issue a POST request that follows the ordering instructions supplied in the task description. If the Observation is missing, emit the placeholder message and **do not** place an order.

## When to Use This Skill
- After a `GET /Observation?...` returns a bundle with at least one entry and the task says *"If low, then order …"*.
- When the task provides a specific lab code (e.g., `MG`, `K`) and a dosing or ordering instruction (e.g., NDC, LOINC code).
- When the task also states *"If no level recorded, don't order anything"*.

## Common Failure Patterns
- Returning only the lab value (e.g., `FINISH(["2.3 mg/dL"])`) and never issuing a `POST /ServiceRequest`.
- Comparing the wrong field (`effectiveDateTime` instead of `valueQuantity.value`).
- Ignoring the unit and comparing a string like `"2.3 mg/dL"` to a numeric threshold.
- Placing an order even when the Observation bundle is empty.

## Recommended Patterns
**Pattern 1: Core decision workflow**
1. Verify the GET response contains `entry[0].resource.valueQuantity.value` and `valueQuantity.unit`.
2. Convert the value to a number (e.g., `float(value)`).
3. Retrieve the low‑threshold for the lab from the task context (hard‑code common thresholds or parse them if supplied).
4. If `value < threshold` **and** the unit matches the expected unit, construct a `ServiceRequest` JSON:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC>", "display": "<Lab Name>" }] },
     "authoredOn": "<CURRENT_TIME>",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/<MRN>" }
   }
   ```
5. POST the JSON to `/ServiceRequest` **before** calling `FINISH`.

**Pattern 2: No Observation fallback**
- If the bundle `total == 0` or the required fields are missing, skip the POST and prepare a human‑readable placeholder such as:
  `"No <lab> level recorded in the last 24 hours for patient <MRN>; no <lab> order placed."`

**Pattern 3: Output formatting**
- After ordering (or deciding not to), call `FINISH` with the lab value **only** when an order was placed, e.g. `FINISH([value])`.
- When no order is placed, return the placeholder string inside the FINISH array.

## Example Application
**Task:** "Check patient S0581164's last serum magnesium level within last 24 hours. If low (<1.5 mg/dL), then order replacement IV magnesium. If no magnesium level has been recorded, don't order anything."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S0581164&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. Extract `valueQuantity.value = 2.1` and `unit = "mg/dL"`.
3. Compare `2.1 < 1.5` → **false**, so **do not** POST an order.
4. Call `FINISH(["2.1 mg/dL"])` (or the placeholder if total==0).

**If the value had been 1.2 mg/dL:**
1‑3 same, condition true.
4. POST the ServiceRequest with the magnesium replacement LOINC code (e.g., `"15074-8"`).
5. `FINISH([1.2])`.

## Success Indicators
- A `POST /ServiceRequest` appears in the agent log **only** when the numeric value is below the defined threshold.
- `FINISH` contains the raw numeric value (or the placeholder) and no extra narrative.
- The ServiceRequest JSON uses the correct LOINC code and references the patient MRN.

## Failure Indicators
- `FINISH` returns only the lab value and no POST was made despite the value being below threshold.
- A POST is made when the Observation bundle is empty or the value is above threshold.
- The posted ServiceRequest lacks required fields (`code.coding[0].code`, `subject.reference`).
- Unit mismatch leads to a failed numeric comparison (e.g., comparing "mmol/L" to a mg/dL threshold).
