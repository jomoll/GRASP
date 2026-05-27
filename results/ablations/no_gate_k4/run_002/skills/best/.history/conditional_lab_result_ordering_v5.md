---
description: "Extend lab\u2011value check to place replacement and optional follow\u2011\
  up orders"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 4
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task4_27
  - task5_19
  - task5_3
  - task4_20
  - task2_30
  - task4_4
  - task10_10
  - task4_15
  update_cycle: 1
tags: []
version: 5
---

# Conditional Lab Result Ordering

## Pattern Description
You must evaluate a recent lab Observation, decide if the value is below a clinically‑relevant threshold, and create the appropriate replacement **ServiceRequest**.  If the task also asks for a paired or follow‑up lab (e.g., "pair this order with a morning serum potassium level to be completed the next day at 8 am"), you must create a second **ServiceRequest** for that future lab.  This pattern centralises the decision‑making, ordering, and FINISH reporting for any lab‑driven replacement workflow.

## When to Use This Skill
- Task text contains a lab code (e.g., `K`, `MG`, `A1C`) and the phrase *"if low then order"*.
- The task also mentions a *follow‑up* or *pair* lab request with a specific time.
- After a GET `Observation?code={code}&patient={MRN}` returns at least one entry.

## Common Failure Patterns
- Agent performs the GET but never extracts the numeric value, so no conditional check occurs.
- Agent creates the replacement order but omits the required follow‑up order.
- Agent posts the ServiceRequest but finishes with a generic "no replacement ordered" message.
- Thresholds are hard‑coded or missing, causing false‑negative ordering.

## Recommended Patterns
**Pattern 1: Extract and evaluate the lab value**
1. From the Observation bundle, take the first entry (most recent).  Use the `valueQuantity.value` field; if the value is a string, fall back to `valueQuantity.value` after parsing.
2. Apply the low‑threshold defined in the task context (e.g., K < 3.5 mmol/L, Mg < 1.5 mg/dL, A1C > 9%).
3. If the value meets the *low* condition, proceed to Pattern 2; otherwise FINISH with a message indicating no replacement needed.

**Pattern 2: Create replacement ServiceRequest**
```json
POST {api_base}/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "{NDC}" }] },
  "authoredOn": "{now}",
  "status": "active",
  "intent": "order",
  "priority": "stat",
  "subject": { "reference": "Patient/{MRN}" }
}
```
Replace `{NDC}` with the replacement drug code supplied in the task context.

**Pattern 3: Optional follow‑up lab order**
1. Detect wording like *"pair this order with"* or *"schedule a repeat {code} test"*.
2. Parse the requested date/time (e.g., "next day at 8am").
3. POST a second ServiceRequest using the original lab `code` and set `occurrenceDateTime` to the parsed timestamp.
```json
POST {api_base}/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "{LOINC}" }] },
  "authoredOn": "{now}",
  "status": "active",
  "intent": "order",
  "priority": "routine",
  "subject": { "reference": "Patient/{MRN}" },
  "occurrenceDateTime": "{follow_up_iso}"
}
```

**Pattern 4: FINISH payload**
- If only replacement was ordered: `FINISH(["replacement {drug} ordered for patient {MRN}"])`
- If both replacement and follow‑up were ordered: `FINISH(["replacement {drug} ordered; follow‑up {code} scheduled for {date}"])`

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217&_sort=-date&_count=1`
2. Extract `valueQuantity.value` → 3.2 (mmol/L).
3. Compare to low threshold 3.5 → low, so proceed.
4. `POST ServiceRequest` for replacement potassium using NDC from task context.
5. Parse "next day at 8am" → `2023-11-14T08:00:00+00:00`.
6. `POST ServiceRequest` for potassium lab with `occurrenceDateTime` set to that timestamp.
7. `FINISH(["replacement potassium ordered; follow‑up potassium scheduled for 2023-11-14T08:00:00+00:00"])`

## Success Indicators
- A replacement ServiceRequest appears in the FHIR server logs.
- If required, a second ServiceRequest with the correct `occurrenceDateTime` is posted.
- FINISH output mentions the ordered actions exactly as described.

## Failure Indicators
- No ServiceRequest POST is observed after a low value.
- FINISH says "no replacement ordered" despite a low lab.
- Follow‑up ServiceRequest missing or has wrong `code`/`occurrenceDateTime`.
- FINISH payload contains explanatory text instead of the prescribed format.
