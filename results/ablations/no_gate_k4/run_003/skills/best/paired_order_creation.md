---
description: "Create a paired follow\u2011up lab order when ordering replacement electrolyte\
  \ therapy"
name: paired_order_creation
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  - task5_16
  update_cycle: 1
tags: []
version: 1
---

# Paired Follow‑up Lab Order for Replacement Electrolyte Therapy

## Pattern Description
You must recognize when a task asks for a replacement electrolyte (e.g., potassium or magnesium) **and** explicitly requests a paired follow‑up laboratory test. The skill adds a second `ServiceRequest` for the specified lab, scheduled for the time indicated (often "next day at 8 am"). This ensures the clinical workflow is complete and satisfies the pairing requirement.

## When to Use This Skill
- The task description contains the phrase *"pair this order with"* followed by a lab name or code (e.g., "serum potassium level") and a timing cue such as "next day at 8am".
- After you have determined, via the observation extraction skill, that the electrolyte value is below the low‑threshold and a replacement order is required.
- The replacement order is being placed via a `ServiceRequest` (NDC or medication code provided in the task context).

## Common Failure Patterns
- Only the replacement `ServiceRequest` is POSTed; the follow‑up lab request is omitted.
- The follow‑up lab is posted but with an incorrect `authoredOn` timestamp (e.g., using the current time instead of the next‑day 08:00).
- The FINISH output mentions the replacement but does not list the paired lab order, causing the evaluator to mark the answer incomplete.

## Recommended Patterns
**Pattern 1: Detect pairing instruction**
1. Scan the task text for the regex `/pair\s+this\s+order\s+with\s+.*?(\b\w+\b)\s+level.*?(next\s+day\s+at\s+(\d{1,2})(?::\d{2})?\s*(am|pm))/i`.
2. Capture the lab name (e.g., "potassium") and the target time (hour, optional minutes, am/pm).
3. Normalize the time to a full ISO‑8601 datetime by adding one day to the current task time and setting the hour/minute accordingly.

**Pattern 2: Build the paired `ServiceRequest`**
- **Replacement order** – use the existing replacement logic (NDC, dosage, patient reference).
- **Follow‑up lab order** – construct a second `ServiceRequest`:
```json
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "priority": "routine",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC_FOR_LAB>", "display": "Serum <LAB>" }] },
  "subject": { "reference": "Patient/<MRN>" },
  "authoredOn": "<NEXT_DAY_08:00_ISO>",
  "note": [{ "text": "Paired with replacement <LAB> order" }]
}
```
- Map the captured lab name to its LOINC code (e.g., potassium → `2823-3`). Maintain a small lookup table inside the skill.

**Pattern 3: POST both resources and report them**
1. `POST /fhir/ServiceRequest` for the replacement order.
2. `POST /fhir/ServiceRequest` for the follow‑up lab order.
3. After both POSTs succeed, call `FINISH` with a concise array describing both actions, e.g.:
```
FINISH(["Replacement potassium ordered", "Paired serum potassium level scheduled for 2023-11-14T08:00:00+00:00"])
```

## Example Application
**Task:** "Check patient S1796597's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET /Observation?code=K&patient=S1796597` → extract latest value (e.g., 3.2 mmol/L) and date.
2. Value < low‑threshold (3.5 mmol/L) → replacement needed.
3. Detect pairing phrase → lab = "potassium", time = next day 08:00.
4. Build replacement `ServiceRequest` (use NDC from task context) and POST.
5. Look up LOINC `2823-3` for serum potassium, compute `2023-11-14T08:00:00+00:00`, build lab `ServiceRequest`, POST.
6. `FINISH(["Replacement potassium ordered", "Paired serum potassium level scheduled for 2023-11-14T08:00:00+00:00"])`

## Success Indicators
- Two `POST /fhir/ServiceRequest` calls appear in the trace (one for medication, one for lab).
- The `FINISH` output lists both actions in a short array, not a free‑text paragraph.
- The lab `ServiceRequest` contains the correct `authoredOn` timestamp (next day 08:00) and the appropriate LOINC code.

## Failure Indicators
- Only one `POST` is made.
- The `FINISH` output mentions only the replacement order or provides a verbose sentence instead of the array format.
- The lab order uses the current time or an incorrect LOINC code.
