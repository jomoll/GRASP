---
description: "Evaluate latest potassium, order replacement and next\u2011day follow\u2011\
  up when low, and return a correctly\u2011typed FINISH response."
name: potassium_check_and_order
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task9_1
  - task9_11
  - task9_6
  - task10_27
  - task9_20
  - task10_21
  - task10_17
  - task9_5
  - task9_14
  update_cycle: 3
tags:
- potassium
- ordering
- format
version: 1
---

# Potassium Level Evaluation and Ordering

## Pattern Description
You must retrieve the most recent serum potassium Observation for the specified patient, extract the numeric value from `valueQuantity.value`, and compare it to the low‑potassium threshold (3.5 mmol/L). If the value is **below** the threshold, you must create two ServiceRequest resources:
1. A replacement potassium order (using the NDC supplied in the task context).
2. A follow‑up serum potassium lab scheduled for the next calendar day at 08:00 local time.
If the value is **at or above** the threshold, no ServiceRequest is created. In all cases the final `FINISH` call must return a **typed** payload (numeric value or boolean flag) rather than a free‑text sentence.

## When to Use This Skill
- Task description mentions *potassium* (code "K") and includes a conditional "if low, then order".
- The agent is about to issue a GET on `Observation?code=K&patient=...`.
- The expected answer is a numeric potassium value **or** an explicit order confirmation, not a prose sentence.

## Common Failure Patterns
- Returning a free‑text string array such as `FINISH(["Potassium level is 3.9 mmol/L, which is above the 3.5 mmol/L threshold."])`.
- Extracting the value from `valueString` or from the `unit` field, resulting in a string like `"3.9 mmol/L"`.
- Omitting the follow‑up ServiceRequest when the potassium is low.
- Using the wrong date filter (e.g., forgetting the 24‑hour window) and therefore picking an outdated Observation.

## Recommended Patterns
**Pattern 1: Retrieve and extract numeric potassium**
1. Issue GET `.../Observation?code=K&patient={MRN}&date=ge{now-24h}`.
2. From the first entry in `Bundle.entry`, read `resource.valueQuantity.value` (a number).
3. Store this as `potassium_value`.
4. Also capture `resource.effectiveDateTime` for possible reporting.

**Pattern 2: Decision and ordering**
- **If** `potassium_value < 3.5` **then**:
  1. POST a `ServiceRequest` for replacement potassium. Use the NDC supplied in the task context (e.g., `code.coding[0].code = "{NDC}"`).
  2. Compute `follow_up_date = now + 1 day` and set the time component to `08:00:00`.
  3. POST a second `ServiceRequest` for a serum potassium lab (LOINC code for serum potassium, e.g., `2823-3`). Set `occurrenceDateTime` to `follow_up_date`.
  4. FINISH with a concise confirmation, e.g. `FINISH([{"potassium":potassium_value,"order":"placed"}])`.
- **Else** (value ≥ 3.5):
  1. No POST calls.
  2. FINISH with the numeric value only, e.g. `FINISH([potassium_value])`.

**Pattern 3: Output formatting**
- Always return a JSON‑compatible array.
- Do **not** embed explanatory sentences inside the array.
- Use numbers for quantitative results and simple objects for status flags.

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium ... also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=K&patient=S3241217&date=ge2023-11-12T10:15:00+00:00`.
2. Extract `potassium_value = 3.9` from `valueQuantity.value`.
3. Since `3.9 >= 3.5`, skip ordering.
4. FINISH with `FINISH([3.9])`.

If the value had been `3.2`:
1‑2. Same GET and extraction (`potassium_value = 3.2`).
3. Create ServiceRequest for replacement potassium (NDC from context) and ServiceRequest for follow‑up lab scheduled for `2023-11-14T08:00:00+00:00`.
4. FINISH with `FINISH([{"potassium":3.2,"order":"placed"}])`.

## Success Indicators
- The GET URL includes the `date=ge{now-24h}` filter.
- `potassium_value` is a plain number extracted from `valueQuantity.value`.
- When low, exactly two POST calls are made (replacement and follow‑up).
- The final FINISH payload is either `[number]` or `[object]`, never a free‑text sentence.

## Failure Indicators
- FINISH contains a string sentence or concatenated unit (e.g., `"3.9 mmol/L"`).
- No ServiceRequest is posted when `potassium_value < 3.5`.
- The date filter is missing, leading to stale observations.
- The follow‑up ServiceRequest uses the wrong date or time.
