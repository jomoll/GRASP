---
description: Handle conditional lab orders and proper FINISH output for missing or
  low values
name: conditional_order_execution
provenance:
  action: MODIFY
  epoch: 4
  fixes: 7
  parent_version: 2
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task9_9
  - task5_16
  - task9_27
  - task5_19
  - task8_5
  - task9_14
  - task9_20
  - task9_28
  - task9_1
  - task8_26
  update_cycle: 0
tags: []
version: 3
---

# Conditional Lab Ordering and FINISH Output

## Pattern Description
You must decide whether to place a replacement medication order (or a follow‑up lab) based on the most recent observation for a given patient. The skill works for any lab where the task specifies a "low" threshold and a replacement order. It also governs the final FINISH payload: when no recent result exists, return the placeholder defined by the task (often `-1` or a short explanatory string); when a result exists, return the numeric value (or the value plus date) and only place orders that are explicitly required.

## When to Use This Skill
- When a task says *"Check the most recent <lab> level. If low, then order replacement <med> and schedule a repeat <lab> for tomorrow.*"
- When the GET `/Observation` response has `total = 0` (no recent measurement).
- When the GET response contains entries but the extracted numeric value is **≥** the low‑threshold defined in the task context.
- When the task expects a numeric answer (e.g., `FINISH([3.5])`) or a tuple `(value, date)` and **must not** embed order flags in the FINISH array.

## Common Failure Patterns
- Posting a repeat lab order even when the original lab is missing or already scheduled.
- Returning `FINISH([-1])` for every conditional task, regardless of whether the placeholder is appropriate.
- Embedding order‑related text inside the FINISH array (e.g., `FINISH(["order placed"])`).
- Using the wrong field (`effectiveDateTime` vs `issued`) to extract the observation timestamp.
- Forgetting to convert `valueQuantity.value` to a plain number before comparison.

## Recommended Patterns
**Pattern 1: Retrieve and validate the observation**
1. Issue `GET {base}/Observation?code={LOINC}&patient={MRN}` (add `date=ge{now-24h}` if the task limits the window).
2. If `total == 0` → **skip ordering** and go to step 4.
3. From the first entry, extract:
   - `value = entry.resource.valueQuantity.value` (numeric)
   - `obsDate = entry.resource.effectiveDateTime` (ISO‑8601 string)
   - Compare `value` to the low‑threshold supplied in the task context.
4. If the observation is missing **or** `value >= threshold` → **no replacement order**.
5. If the observation exists **and** `value < threshold` → proceed to Pattern 2.

**Pattern 2: Place required orders**
- Build a `ServiceRequest` for the replacement medication using the NDC or code given in the task.
- If the task also asks for a follow‑up lab, create a second `ServiceRequest` with:
  - `code.coding[0].code` = same LOINC as the original lab
  - `occurrenceDateTime` = `{now + 1 day}T08:00:00+00:00`
  - `note` must be an **array** of objects: `[{"text": "..."}]`
- POST each request **only** when the conditions above are met.

**Pattern 3: Construct the FINISH payload**
- If the observation was missing and the task defines `-1` as the sentinel → `FINISH([-1])`.
- If the task expects a descriptive string for “no result” → `FINISH(["No recent <lab> recorded; no order placed."])`.
- If a value was found → `FINISH([value])` **or** `FINISH([value, obsDate])` when the date is required.
- **Never** include order‑related text or flags inside the FINISH array.

## Example Application
**Task:** "Check patient S1311412's most recent potassium level. If low, order replacement potassium and schedule a serum potassium draw tomorrow at 08:00."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=2823-3&patient=S1311412`
2. Response `total = 0` → skip ordering.
3. FINISH payload: `FINISH([-1])` (task defined `-1` for missing value).

If the response had `total = 1` with `valueQuantity.value = 3.0` and the low‑threshold is `3.5`:
1. Value < 3.5 → need orders.
2. POST replacement potassium `ServiceRequest` (use NDC from task).
3. POST follow‑up potassium `ServiceRequest` with `occurrenceDateTime = 2023-11-14T08:00:00+00:00`.
4. FINISH payload: `FINISH([3.0])`.

## Success Indicators
- No `ServiceRequest` is posted when the observation is missing or not low.
- When a low value is detected, exactly the required `ServiceRequest`s are posted, and each `note` field is an array.
- FINISH contains only the numeric value (or sentinel) and optional date, never order text.

## Failure Indicators
- A `ServiceRequest` appears in the log for a task where the lab was missing or normal.
- FINISH array includes strings like "order placed" or the placeholder `-1` when the task expects a numeric value.
- `note` in a `ServiceRequest` is a single object instead of an array.
- The agent extracts `effectiveDateTime` instead of `valueQuantity.value` for the numeric comparison.
