---
description: "Verify the date of the most recent procedure and order a repeat study\
  \ if older than 12\u202Fmonths"
name: procedure_age_check
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task8_7
  - task8_29
  - task1_10
  - task3_30
  - task8_23
  - task3_1
  - task4_11
  - task2_28
  - task3_14
  update_cycle: 0
tags:
- procedure
- age
- repeat-study
version: 1
---

# Procedure Age Check

## Pattern Description
You must determine whether a patient’s most recent instance of a specific procedure (identified by one or more CPT codes) is older than a configurable time window (default 12 months). If the procedure is missing or the latest date exceeds the window, you create a new `ServiceRequest` (or `Procedure` request) with the supplied CPT code and indication. This pattern is reusable for any imaging or therapeutic procedure where periodic repeat imaging is required.

## When to Use This Skill
- When a task asks for the date of the most recent CT Abdomen, MRI, colonoscopy, etc., **and** specifies a re‑order rule based on age (e.g., “if performed more than 12 months ago, order a new study”).
- When the instruction provides:
  - One or more CPT codes for the existing study (e.g., `IMGCT0491,IMGIL0001`).
  - A CPT code for the new study to be ordered (e.g., `74177`).
  - An indication text for the new order (e.g., `Renal mass follow‑up`).

## Common Failure Patterns
- Using only a date range filter that limits the search to the past year, which hides older studies and leads the agent to assume a recent study exists.
- Extracting the wrong date field (`issued` instead of `performedPeriod.start` or `performedDateTime`).
- Forgetting to compare the extracted date to the current/reference date before deciding to order.
- Ordering a new study even when a recent one is present because the agent never examined the returned bundle entries.

## Recommended Patterns
**Pattern 1: Retrieve the full list of relevant procedures**
1. Build a GET request that **does not limit the date range** (unless the API requires it). Example:
   ```
   GET /fhir/Procedure?patient={patient_id}&code={cpt_codes}
   ```
2. Inspect the `Bundle.entry` array. If `total == 0`, treat as “no prior study”.
3. For each entry, locate the performed date:
   - Prefer `performedPeriod.start` if present.
   - Fallback to `performedDateTime`.
   - If both are missing, skip that entry.
4. Identify the **most recent** date among the valid entries.

**Pattern 2: Age comparison and decision**
1. Parse the most‑recent date as an ISO‑8601 timestamp.
2. Compute the difference between the reference date (usually the task’s “now” timestamp) and the procedure date.
3. If the difference > 12 months (or the configured window), **order a new study**; otherwise, **do not order**.
4. If no prior study was found, also order a new study.

**Pattern 3: Construct the ServiceRequest**
```json
{
  "resourceType": "ServiceRequest",
  "code": {
    "coding": [{
      "system": "http://www.ama-assn.org/go/cpt",
      "code": "{new_cpt}",
      "display": "{new_cpt_display}"
    }]
  },
  "authoredOn": "{now_iso}",
  "status": "active",
  "intent": "order",
  "priority": "routine",
  "subject": { "reference": "Patient/{patient_id}" },
  "note": [{ "text": "{indication}" }],
  "occurrenceDateTime": "{now_iso}"
}
```
- **CORRECT**: `code.coding[0].code` set to the new CPT, `note.text` contains the indication.
- **WRONG**: Using the old CPT code in the request body, or omitting the `note`.

## Example Application
**Task:** “Find the date of the most recent CT Abdomen for patient S3032536. If the study was performed more than 12 months ago, order a new CT Abdomen with IV contrast indication ‘Renal mass follow‑up’.”

**Step‑by‑step:**
1. `GET /fhir/Procedure?patient=S3032536&code=IMGCT0491,IMGIL0001`
2. Parse the bundle. Suppose the latest entry has `performedPeriod.start = 2022‑10‑05T09:30:00Z`.
3. Compare to the reference date `2023‑11‑07T22:47:00Z` → 13 months → exceeds 12 months.
4. Build the ServiceRequest using CPT `74177` and indication `Renal mass follow‑up` (see Pattern 3).
5. `POST /fhir/ServiceRequest` with the JSON body.
6. `FINISH(["Most recent CT Abdomen was performed on 2022‑10‑05. New study ordered (CPT 74177)."])

**CORRECT output:** `FINISH(["Most recent CT Abdomen was performed on 2022‑10‑05. New study ordered (CPT 74177)."])`
**WRONG output:** `FINISH(["CT Abdomen performed on 2022‑10‑05, within 12 months."])` (fails to order when needed).

## Success Indicators
- The agent issues a single GET without a restrictive `date=` filter.
- The agent extracts the most recent `performedPeriod.start` (or `performedDateTime`).
- The agent correctly decides whether to POST a new `ServiceRequest` based on a 12‑month comparison.
- The POST body contains the new CPT code and the indication note.
- The final FINISH message reports the correct date and action.

## Failure Indicators
- The GET request includes `date=ge...&date=le...` that limits results to the past year, causing older studies to be missed.
- The agent compares the wrong field (e.g., `issued` on a MedicationRequest) or ignores the date entirely.
- The agent always orders a new study regardless of the age check.
- The POST body uses the old CPT code or omits the indication.
- The FINISH output does not mention the date of the prior study when one exists.

---
*This skill is reusable for any repeat‑procedure scenario where timing dictates a new order.*
