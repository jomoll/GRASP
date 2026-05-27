---
description: "Generic low\u2011value lab check and replacement order for electrolytes\
  \ and other labs"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 5
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
tags:
- lab
- conditional-order
- electrolyte
- replacement
version: 6
---

# conditional_lab_result_ordering

## Pattern Description
You must evaluate a recent lab result and, if it falls below a clinically‑relevant low threshold, automatically create a replacement ServiceRequest. The skill works for any lab where the task mentions a conditional order (e.g., magnesium, potassium, calcium) and supplies either an explicit threshold or a default one you can infer.

## When to Use This Skill
- The task asks to *check the last X level* within a time window **and** says “if low, then order replacement …”.
- The task may also specify a custom low‑value cutoff (e.g., “< 1.5 mg/dL”) or rely on a standard reference range.
- The task may include the NDC or LOINC code for the replacement medication.

## Common Failure Patterns
- No ServiceRequest is posted even though the lab value is below the threshold.
- The replacement order uses the wrong medication code or omits required fields (`authoredOn`, `status`, `intent`).
- The agent posts an order when the lab value is normal or when no recent result exists.
- The low‑value threshold is missed because it is embedded in free‑text.

## Recommended Patterns
**Pattern 1: Retrieve the most recent lab**
1. Build the Observation GET URL with the appropriate `code` and patient ID, adding a date range if the task limits it.
2. Request sorting by `-date` and limit to 1 (`_sort=-date&_count=1`).
3. If `Bundle.total == 0` → **no recent result** → skip ordering and finish with a “no result” message.

**Pattern 2: Extract numeric value**
1. Use the `value_only_extraction` skill to pull `valueQuantity.value` (or `valueString` parsed to a number).
2. If the value includes a unit, strip it; convert to the unit required by the task if necessary.

**Pattern 3: Determine low‑value threshold**
- Look for a pattern like `<\s*([0-9.]+)\s*([a-zA-Z/]+)` in the task text.
- If none is found, fall back to a default per‑lab table (e.g., Mg < 1.5 mg/dL, K < 3.5 mmol/L).

**Pattern 4: Conditional ordering**
1. Compare the extracted value to the threshold.
2. If `value < threshold`:
   - Construct a ServiceRequest JSON:
     ```json
     {
       "resourceType": "ServiceRequest",
       "code": { "coding": [{ "system": "http://loinc.org", "code": "<replacement‑LOINC>", "display": "<display>" }] },
       "authoredOn": "<current‑ISO‑time>",
       "status": "active",
       "intent": "order",
       "priority": "stat",
       "subject": { "reference": "Patient/<MRN>" },
       "note": { "text": "Ordered because recent <lab> result (<value> <unit>) is below threshold (<threshold> <unit>)." }
     }
     ```
   - POST to `/ServiceRequest`.
   - `FINISH(["<lab> replacement ordered"])`.
3. Else (value ≥ threshold):
   - `FINISH(["no replacement ordered"])`.

**Pattern 5: Verification before FINISH**
- Ensure the ServiceRequest POST succeeded (check system note or response status).
- If the POST failed, fall back to a safe message: `FINISH(["order failed; no replacement ordered"])`.

## Example Application
**Task:** “Check patient S1733937's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don’t order anything.”

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S1733937&date=ge2023‑11‑12T10:15:00&date=le2023‑11‑13T10:15:00&_sort=-date&_count=1`
2. Response contains a result with `valueQuantity.value = 1.2` mg/dL.
3. No explicit threshold in task → use default Mg < 1.5 mg/dL.
4. `1.2 < 1.5` → construct ServiceRequest with the NDC/LOINC for IV magnesium (extracted from task or a default mapping).
5. POST ServiceRequest.
6. `FINISH(["magnesium replacement ordered"])`.

**CORRECT output:** `FINISH(["magnesium replacement ordered"])`
**WRONG output:** `FINISH(["no replacement ordered"])` when the value is actually low.

## Success Indicators
- A ServiceRequest is posted **only** when the lab value is below the identified threshold.
- FINISH payload clearly states the ordering decision (e.g., `"magnesium replacement ordered"`).
- No ordering occurs when the result is normal or absent.

## Failure Indicators
- ServiceRequest posted despite a normal or missing lab value.
- No ServiceRequest posted when the value is below threshold.
- FINISH message does not match the ordering decision (e.g., says “no replacement ordered” when an order was made).
