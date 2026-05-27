---
description: "Add low\u2011magnesium detection and ordering logic to the electrolyte\
  \ replacement skill"
name: electrolyte_replacement_service_request
provenance:
  action: MODIFY
  blind_select: random
  epoch: 4
  fixes_unused: 2
  parent_version: 2
  probe_score_unused: -2
  regressions_unused: 1
  triggering_sample_ids:
  - task8_23
  - task9_9
  - task5_16
  - task9_27
  - task5_19
  - task8_5
  - task8_14
  - task10_24
  - task3_17
  - task9_14
  update_cycle: 0
tags: []
version: 3
---

# Electrolyte Replacement Service Request with Low Value Evaluation

## Pattern Description
You must evaluate the most recent electrolyte observation (e.g., magnesium) and decide whether a replacement ServiceRequest is required. The skill first extracts the numeric value from the Observation, compares it to a clinically‑relevant low‑threshold, and then either creates a concise replacement order or returns a short "no action" message. This pattern is reusable for any electrolyte where a low‑value rule exists (magnesium, potassium, calcium, etc.).

## When to Use This Skill
- When a task asks to *check the last serum magnesium (or other electrolyte) level within the past 24 hours* and *order replacement if the value is low*.
- When the task explicitly says *"If no level is recorded, do nothing"*.
- When the expected answer is a one‑sentence decision string (e.g., "Magnesium replacement ordered") or a ServiceRequest POST.

## Common Failure Patterns
- The skill returns a generic "normal" or "not recorded" message without evaluating the numeric value.
- The skill never creates a ServiceRequest even when the extracted value is below the low‑threshold.
- The skill includes extra explanatory text instead of the required concise decision string.
- The skill looks at the wrong field (e.g., `valueString` instead of `valueQuantity.value`).

## Recommended Patterns
**Pattern 1: Extract numeric electrolyte value**
1. From the Observation Bundle, locate the first entry where `resource.resourceType == "Observation"`.
2. Read `resource.valueQuantity.value` as a number.  
   - **CORRECT**: `valueQuantity.value` → `1.2`
   - **WRONG**: `valueQuantity` concatenated with `unit` → `"1.2 mg/dL"`
3. If the Observation is missing or `valueQuantity` is absent, treat the result as *not recorded*.

**Pattern 2: Low‑value decision rule**
1. Define a low‑threshold for magnesium (e.g., `< 1.5 mg/dL`).
2. If the extracted value exists and is **< threshold**:
   - Construct a `ServiceRequest` POST with the NDC or LOINC code supplied in the task context.
   - Use a concise FINISH message: `"Magnesium replacement ordered"`.
3. If the value exists and is **≥ threshold**:
   - FINISH with `"Magnesium level normal; no replacement ordered"`.
4. If no observation was found in the 24‑hour window:
   - FINISH with `"Magnesium level not recorded; no replacement ordered"`.

**Pattern 3: Formatting the final output**
- Always return a single‑element array containing the exact decision string (no extra punctuation or explanation).
- When a ServiceRequest is created, still return the concise decision string after the POST succeeds.

## Example Application
**Task:** "Check patient S1023381's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1023381&date=ge2023-11-12T10:15:00+00:00`
2. Parse the Bundle; extract `valueQuantity.value` → `1.3`.
3. Compare to threshold `1.5` → **low**.
4. `POST http://localhost:8080/fhir/ServiceRequest` with body containing the NDC for IV magnesium (provided in task context).
5. After successful POST, `FINISH(["Magnesium replacement ordered"])`.

**If the value had been `1.8`** → `FINISH(["Magnesium level normal; no replacement ordered"])`.

**If the Bundle `total` was `0`** → `FINISH(["Magnesium level not recorded; no replacement ordered"])`.

## Success Indicators
- The agent creates a `ServiceRequest` POST **only** when the extracted value is below the low‑threshold.
- The FINISH output is a single‑element array with exactly one of the three allowed strings.
- No extra explanatory text appears in the FINISH payload.

## Failure Indicators
- The agent returns a generic "normal" message without checking the numeric value.
- The agent fails to POST a ServiceRequest when the value is low.
- The FINISH payload contains additional words, brackets, or JSON structures beyond the required string.
- The agent reads `valueString` or other non‑numeric fields for the comparison.
