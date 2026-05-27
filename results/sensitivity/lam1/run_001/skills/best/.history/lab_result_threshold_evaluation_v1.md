---
description: "Enforces correct low\u2011threshold checks for lab results and conditional\
  \ ordering of replacements."
name: lab_result_threshold_evaluation
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task9_28
  - task4_4
  - task5_7
  update_cycle: 1
tags: []
version: 1
---

# Lab Result Threshold Evaluation

## Pattern Description
You must treat any task that asks to *check a lab value and act on a low result* as a reusable pattern. First, retrieve the most recent Observation for the specified code, extract the numeric value, and compare it against a clinically‑defined low‑threshold (e.g., magnesium < 1.5 mg/dL, potassium < 3.5 mmol/L). Only when the value is **below** the threshold should you create an order (MedicationRequest or ServiceRequest) using the provided NDC or dosing instructions. If the value is normal or no recent result exists, simply finish with a concise message—do **not** fabricate a “normal” interpretation or mention thresholds that were not part of the task.

## When to Use This Skill
- The task description contains phrases like *"check … level", "if low then order", "within last 24 hours"*.
- The task provides a lab code (e.g., `MG` for magnesium, `K` for potassium) and may include dosing or NDC details.
- A `GET /Observation` request for that code is present (or should be issued) before any decision logic.
- No prior ordering action has been taken for the same lab in the current trace.

## Common Failure Patterns
- Interpreting the value as "normal" or "above threshold" without checking the *low* threshold.
- Returning free‑text explanations instead of the required JSON array payload.
- Using the wrong field (`valueString` or `valueQuantity.unit`) leading to string‑based comparisons.
- Ordering a replacement even when the observation is missing or the value is above the low threshold.
- Omitting the date filter (`date=ge{now-24h}`) and using stale results.

## Recommended Patterns
**Pattern 1: Retrieve the latest relevant Observation**
1. Issue `GET {api_base}/Observation?code={CODE}&patient={PATIENT_REF}&date=ge{NOW-24h}`.
2. Verify the response is a `Bundle` with `total >= 1`.
3. From the first entry, extract `valueQuantity.value` (numeric) and `valueQuantity.unit` if needed.
4. Also capture `effectiveDateTime` for possible reporting.

**Pattern 2: Apply low‑threshold decision rule**
- Define low thresholds (example values; adjust per institutional policy):
  - Magnesium (MG): **1.5 mg/dL**
  - Potassium (K): **3.5 mmol/L**
- If the extracted numeric value **< low_threshold** → proceed to Pattern 3.
- Else → `FINISH(["No replacement needed; latest level {value}{unit} is within normal range."])`.

**Pattern 3: Conditional ordering**
1. Build a `MedicationRequest` (or `ServiceRequest` if the task specifies) using the NDC or dosing instructions supplied in the task context.
2. Include `subject.reference` pointing to the patient, `authoredOn` set to the current timestamp, and any required `dosageInstruction`.
3. `POST` the request to `{api_base}/MedicationRequest` (or `/ServiceRequest`).
4. After successful POST, `FINISH(["Replacement ordered for {lab_name} low result {value}{unit}."])`.

**Pattern 4: No recent result fallback**
- If the Observation bundle has `total == 0`, skip ordering and `FINISH(["No recent {lab_name} level within the last 24 hours; no replacement ordered."])`.

## Example Application
**Task:** "Check patient S3057899's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=Patient/S3057899&date=ge2023-11-12T10:15:00Z`
2. Bundle returned with one entry; extract `valueQuantity.value = 1.2` and `unit = "mg/dL"`.
3. Compare: `1.2 < 1.5` → low.
4. Construct MedicationRequest using the NDC from task context and POST it.
5. `FINISH(["Replacement ordered for magnesium low result 1.2mg/dL."])`.

**If the bundle had `total == 0`** → `FINISH(["No recent magnesium level within the last 24 hours; no replacement ordered."])`.

## Success Indicators
- A `GET /Observation` with the correct `code` and 24‑hour date filter appears before any decision.
- The extracted value is compared against the low‑threshold, not the high‑threshold.
- `POST` is only executed when the value is below the threshold.
- Final `FINISH` payload is a JSON array containing a single short string (no extra explanations).

## Failure Indicators
- The agent reports "normal" or mentions a high‑threshold that was never part of the task.
- `FINISH` contains free‑text sentences or arrays with more than one element.
- An order is posted when the observation is missing or the value is above the low threshold.
- The Observation value is taken from `valueString` or includes the unit in the comparison.
