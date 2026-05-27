---
description: "Place replacement orders when a recent lab value is below its low\u2011\
  threshold and schedule a follow\u2011up test."
name: conditional_lab_replacement_order
provenance:
  action: ADD
  epoch: 1
  fixes: 13
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - task9_27
  - task10_20
  - task10_17
  - task4_28
  - task10_8
  - task10_24
  update_cycle: 0
tags:
- lab
- conditional-order
- electrolyte-replacement
version: 1
---

# Conditional Lab Replacement Order

## Pattern Description
You must automatically create a replacement **ServiceRequest** when a recent laboratory observation is below a predefined low‑threshold. This pattern applies to electrolytes (e.g., potassium, magnesium) and other labs where replacement therapy is indicated. After ordering the replacement, optionally schedule a follow‑up observation (e.g., a repeat serum level the next morning). The skill isolates three reusable steps: (1) locate the most recent observation for the requested code, (2) compare the numeric result to a configurable low‑limit, and (3) construct the appropriate `ServiceRequest` payload(s).

## When to Use This Skill
- When the task description says *"If low, then order replacement ..."* for a lab identified by a code (e.g., `K`, `MG`).
- When the task also asks to *pair the order with a follow‑up lab* (e.g., "order a morning serum potassium level to be completed the next day at 8 am").
- When the task provides an NDC or LOINC code for the replacement medication or the follow‑up test.
- When a recent observation within the required time window (usually 24 h) is available.

## Common Failure Patterns
- Returning only the numeric value without taking ordering action.
- Comparing the wrong field (`valueString` instead of `valueQuantity.value`).
- Using the wrong threshold (e.g., high‑threshold instead of low‑threshold).
- Omitting the follow‑up `ServiceRequest` when the task explicitly requests it.
- Posting an order with missing required fields (`status`, `intent`, `subject`).

## Recommended Patterns
**Pattern 1: Locate and extract the recent lab value**
1. Issue `GET {base}/Observation?code={labCode}&patient={patientId}`.
2. From the returned Bundle, select the entry with the most recent `effectiveDateTime` that is within the required window (e.g., last 24 h).
3. Extract the numeric result:
   - Prefer `valueQuantity.value` (number).
   - If only `valueString` is present, parse the leading number.
4. If no qualifying observation is found, **FINISH([])** – do not place any order.

**Pattern 2: Compare to low‑threshold and decide**
- Maintain a mapping table (example below) of lab codes to low‑thresholds and replacement NDCs.
- If `extractedValue < lowThreshold` → proceed to ordering.
- Otherwise, **FINISH([extractedValue])** or a message indicating the value is within goal.

**Pattern 3: Construct replacement ServiceRequest**
```json
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "priority": "stat",
  "code": {
    "coding": [{
      "system": "http://www.nlm.nih.gov/research/umls",
      "code": "{replacementNDC}",
      "display": "{replacementName}"
    }]
  },
  "subject": { "reference": "Patient/{patientId}" },
  "authoredOn": "{nowISO}"
}
```
- Replace placeholders with actual values.
- Include any dosage instructions if provided in the task context.

**Pattern 4: Optional follow‑up lab ServiceRequest**
If the task requests a repeat lab:
```json
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "priority": "routine",
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "{labLOINC}",
      "display": "{labDisplay}"
    }]
  },
  "subject": { "reference": "Patient/{patientId}" },
  "occurrenceDateTime": "{nextDay8amISO}",
  "authoredOn": "{nowISO}"
}
```
- `nextDay8amISO` = current date + 1 day at `08:00:00` in ISO‑8601.

## Example Application
**Task:** "Check patient S1311412's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1311412`
2. Choose the newest entry (e.g., `effectiveDateTime = 2023‑11‑12T09:30:00Z`).
3. Extract `valueQuantity.value = 3.2` (mmol/L).
4. Low‑threshold for potassium = **3.5** mmol/L → 3.2 < 3.5, so order.
5. POST replacement ServiceRequest (use NDC supplied in task context, e.g., `12345‑6789‑01`).
6. Compute `nextDay8amISO = 2023‑11‑14T08:00:00Z`.
7. POST follow‑up ServiceRequest for potassium (LOINC `2823‑3`).
8. `FINISH([3.2])` (or any required output format).

**CORRECT output example:**
```json
FINISH([3.2])
```
**WRONG output example:**
```json
FINISH(["Potassium is low, order placed."])
```

## Success Indicators
- A `ServiceRequest` POST is observed with the correct replacement NDC and patient reference.
- When a follow‑up is required, a second `ServiceRequest` with `occurrenceDateTime` set to next‑day 08:00 is posted.
- The final `FINISH` contains the raw numeric lab value (or `-1` if no recent observation).

## Failure Indicators
- No `ServiceRequest` POST despite a low value.
- `FINISH` returns a string message instead of a numeric array.
- The posted `ServiceRequest` is missing `code.coding.code` (NDC) or has the wrong patient reference.
- Follow‑up `ServiceRequest` is omitted when the task explicitly asks for it.
