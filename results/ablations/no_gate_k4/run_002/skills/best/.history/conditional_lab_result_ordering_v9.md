---
description: "Add low\u2011value check, create replacement order, and schedule paired\
  \ follow\u2011up lab"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 8
  triggering_sample_ids:
  - task4_27
  - task9_9
  - task5_16
  - task9_27
  - task2_26
  - task5_19
  - task2_16
  - task10_24
  - task9_14
  - task10_21
  update_cycle: 0
tags: []
version: 9
---

# Conditional Lab Result Ordering with Follow‑Up Scheduling

## Pattern Description
You must evaluate a lab Observation, decide if the result is below a clinically‑relevant threshold, and automatically create a replacement **ServiceRequest**. When the replacement order requires a paired follow‑up (e.g., a repeat potassium level the next morning), you must also schedule that follow‑up by invoking the existing `follow_up_lab_ordering` skill or by creating a second ServiceRequest with the appropriate timing.

## When to Use This Skill
- When a task asks to *check the most recent* lab value (e.g., potassium, magnesium) and *order replacement* if the value is low.
- When the task also specifies a *paired follow‑up lab* to be performed after the replacement (e.g., “order a morning serum potassium level tomorrow at 8 am”).
- When the agent has already performed a GET on the Observation resource and received a Bundle with at least one entry.

## Common Failure Patterns
- The agent extracts the lab value but never compares it to the low‑threshold, resulting in `FINISH(["no replacement ordered"])` even when the value is low.
- The agent creates the replacement order but forgets to schedule the required follow‑up, violating the task’s pairing instruction.
- The agent posts a ServiceRequest with missing required fields (e.g., no `code.coding`, no `subject.reference`).
- The agent posts the replacement order but does not include the dosing instructions supplied in the task context.

## Recommended Patterns
**Pattern 1: Extract and evaluate the lab value**
1. Locate the first entry in the Bundle (`entry[0].resource`).
2. Read `valueQuantity.value` as a number and `valueQuantity.unit` as a string.
3. Convert the value to the standard unit if needed (e.g., potassium in `mmol/L`, magnesium in `mg/dL`).
4. Compare against the low‑threshold defined in the task (e.g., potassium < 3.5 mmol/L, magnesium < 1.5 mg/dL).

**Pattern 2: Create the replacement ServiceRequest**
```json
POST {api_base}/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "<NDC_OR_CODE>", "display": "Replacement <SUBSTANCE>" }] },
  "status": "active",
  "intent": "order",
  "subject": { "reference": "Patient/<MRN>" },
  "note": { "text": "<dosing instructions from task>" }
}
```
5. Verify the POST response is successful before proceeding.

**Pattern 3: Schedule the paired follow‑up lab**
- If the task mentions a follow‑up (e.g., “morning serum potassium level tomorrow at 8 am”), call the existing `follow_up_lab_ordering` skill with the appropriate parameters, **or** create a second ServiceRequest of type `lab` with `authoredOn` set to the desired datetime and `code` set to the original lab code.

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217&_sort=-date&_count=1`
2. From the returned Bundle, extract `valueQuantity.value = 3.2` and `valueQuantity.unit = "mmol/L"`.
3. Compare: `3.2 < 3.5` → low.
4. `POST` a replacement potassium ServiceRequest using the NDC supplied in the task context.
5. Immediately `POST` a follow‑up potassium ServiceRequest with `authoredOn = 2023‑11‑14T08:00:00+00:00` (next day 8 am).
6. `FINISH(["replacement potassium ordered", "follow‑up potassium scheduled for 2023‑11‑14 08:00"] )`

**CORRECT output:** `FINISH(["replacement potassium ordered", "follow‑up potassium scheduled for 2023‑11‑14 08:00"])`
**WRONG output:** `FINISH(["no replacement ordered"])`

## Success Indicators
- A ServiceRequest for the replacement appears in the FHIR server.
- A second ServiceRequest (or a call to `follow_up_lab_ordering`) for the paired lab is present with the correct `authoredOn` datetime.
- The final FINISH output mentions both the replacement and the scheduled follow‑up.

## Failure Indicators
- FINISH output only mentions “no replacement ordered” despite a low value.
- Replacement ServiceRequest is posted but the follow‑up request is missing.
- The posted ServiceRequest lacks required fields (`code.coding`, `subject.reference`, or dosing note).
