---
description: "Add threshold checks, stale\u2011date logic and paired follow\u2011\
  up ordering for lab\u2011driven replacement requests"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 10
  triggering_sample_ids:
  - task10_13
  - task9_5
  - task9_22
  - task5_7
  - task10_10
  - task1_10
  - task5_3
  - task10_15
  - task10_18
  - task5_17
  update_cycle: 1
tags:
- lab
- conditional-ordering
- threshold
- follow-up
version: 11
---

# Conditional Lab Result Ordering with Thresholds and Follow‑up Pairing

## Pattern Description
You must decide whether to create a replacement **ServiceRequest** based on the most recent lab **Observation**.  The decision hinges on two reusable patterns:
1. **Numeric threshold check** – compare the lab value (extracted from `valueQuantity.value` or a numeric `valueString`) against a clinically‑defined low‑limit for that test code.
2. **Stale‑date check** – if the task asks to order a repeat test when the last result is older than a given interval (e.g., > 1 year), compare the observation’s `effectiveDateTime` to the current time.
If the condition is met, you must also handle any *paired* follow‑up order described in the task (e.g., “order a morning serum potassium level for the next day at 8 am”).

## When to Use This Skill
- After a `GET Observation?...code={CODE}&patient={MRN}&_sort=-date&_count=1` returns a bundle with at least one entry **and** the task text contains phrases like:
  - “If low, then order replacement …”
  - “If the result date is greater than X, order a new … test.”
  - “Pair this order with … next day at 8 am.”
- When the bundle is empty **and** the task explicitly says *don’t order anything* if no recent result exists.

## Common Failure Patterns
- Ignoring the numeric value and always returning “no replacement ordered”.
- Comparing the wrong field (`valueString` that includes units) instead of the pure numeric `valueQuantity.value`.
- Not checking the result date, so stale results never trigger a repeat order.
- Failing to create the required *paired* follow‑up ServiceRequest.
- Ordering when the observation is within the acceptable range or recent enough.

## Recommended Patterns
**Pattern 1: Extract and evaluate the lab value**
1. Verify the bundle `total > 0`. If `0`, skip ordering and `FINISH(["no replacement ordered"])`.
2. From the first entry, read:
   - `value = entry.resource.valueQuantity?.value` **or** parse a numeric prefix from `valueString`.
   - `unit = entry.resource.valueQuantity?.unit` (optional, for logging).
3. Look up the low‑limit for the requested `code` (e.g., `K` → 3.5 mmol/L, `MG` → 1.5 mg/dL). This mapping is hard‑coded in the skill.
4. If `value < low_limit` → **proceed to ordering**.
5. If the task mentions a date‑age rule, also:
   - Parse `obsDate = entry.resource.effectiveDateTime`.
   - Compute `ageDays = now - obsDate`.
   - If `ageDays > thresholdDays` (e.g., 365) → **proceed to ordering**.

**Pattern 2: Build the replacement ServiceRequest**
1. Create a `ServiceRequest` JSON with:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "{NDC_REPLACEMENT}", "display": "Replacement {SUBSTANCE}" }] },
     "status": "active",
     "intent": "order",
     "subject": { "reference": "Patient/{MRN}" },
     "authoredOn": "{NOW_ISO}",
     "note": [{ "text": "{FREE_TEXT_INSTRUCTION}" }]
   }
   ```
2. If the task requests a *paired* follow‑up lab, add a second `ServiceRequest` with:
   - `code` set to the LOINC code of the follow‑up test.
   - `occurrenceTiming` set to the next day at the specified hour (e.g., `2023-11-14T08:00:00+00:00`).
3. POST each request to `/fhir/ServiceRequest` before calling `FINISH`.

**Pattern 3: Completion output**
- After successful POST(s), `FINISH` must echo any free‑text notes from the created ServiceRequests (handled by `action_answer_consistency_check`).
- If no order was created, output exactly `FINISH(["no replacement ordered"])`.

## Example Application
**Task:** "Check patient S1796597's most recent potassium level. If low, then order replacement potassium … also pair this order with a morning serum potassium level to be completed the next day at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1796597&_sort=-date&_count=1`
2. Bundle contains an entry with `valueQuantity.value = 3.2` (mmol/L).
3. Low‑limit for K = 3.5 → 3.2 < 3.5, condition met.
4. Build replacement request using the NDC supplied in the task (e.g., `12345‑6789‑01`).
5. Build paired follow‑up request with LOINC for serum potassium and `occurrenceTiming = "2023-11-14T08:00:00+00:00"`.
6. POST both ServiceRequests.
7. `FINISH(["replacement potassium ordered for patient S1796597","morning serum potassium ordered for 2023-11-14T08:00:00+00:00"])`.

## Success Indicators
- A `POST /fhir/ServiceRequest` is issued when the lab value is below the threshold or the result date exceeds the age limit.
- The posted body contains the correct `code.coding.code` (NDC) and `subject.reference`.
- If a paired order is required, a second ServiceRequest with the proper `occurrenceTiming` is posted.
- `FINISH` output includes the free‑text note from the order(s).

## Failure Indicators
- The agent returns `FINISH(["no replacement ordered"])` despite the lab value being below the low‑limit.
- The agent creates an order when the value is normal or the result is recent enough.
- The posted ServiceRequest is missing the NDC code or the patient reference.
- No paired follow‑up request is posted when the task explicitly asks for one.
- The agent skips the date‑age check for stale results (e.g., HbA1c > 1 year old).
