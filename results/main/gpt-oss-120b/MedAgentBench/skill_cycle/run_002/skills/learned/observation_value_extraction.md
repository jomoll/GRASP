---
description: Extract numeric lab value and timestamp, return -1 when missing (no placeholder
  strings)
name: observation_value_extraction
provenance:
  action: MODIFY
  epoch: 3
  fixes: 3
  parent_version: 3
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task9_9
  - task9_28
  - task9_3
  - task4_28
  - task9_14
  - task5_16
  - task9_6
  - task9_20
  update_cycle: 1
tags:
- observation
- extraction
- lab-values
version: 4
---

# Observation Value Extraction

## Pattern Description
You must reliably pull a numeric result and its observation timestamp from a FHIR Observation bundle. This capability is needed whenever a task asks for the latest lab value (e.g., magnesium, potassium, HbA1c) and may later require a decision based on that value. The skill should always return a plain numeric value together with an ISO‑8601 timestamp, or the sentinel `-1` when no suitable observation exists. No free‑text placeholders are allowed.

## When to Use This Skill
- When a task requests "the most recent *X* level" (lab, electrolyte, etc.)
- When a task asks for "the last *Y* value and when it was recorded"
- When a conditional order depends on a numeric lab result (e.g., "if low, order replacement")
- When the Observation search may return multiple entries; you need the newest within a time window.

## Common Failure Patterns
- Returning a string like `"No magnesium replacement needed"` instead of the numeric value.
- Omitting the timestamp entirely.
- Using `valueString` that contains units (e.g., `"3.5 mmol/L"`) without stripping the unit.
- Returning an empty array `[]` or a placeholder `[-1]` when a valid observation exists.
- Selecting the wrong entry (e.g., the oldest instead of the most recent).

## Recommended Patterns
**Pattern 1: Core extraction strategy**
1. **Search**: GET `/Observation?code={code}&patient={MRN}` (add `date=ge{now-24h}` if a time window is required).
2. **Validate response**: Ensure `Bundle.entry` is present and non‑empty.
3. **Select newest**: Sort entries by `resource.effectiveDateTime` (or `issued` if `effectiveDateTime` missing) descending; pick the first.
4. **Extract numeric value**:
   - Prefer `resource.valueQuantity.value` (already a number).
   - If only `valueString` is present, parse the leading numeric token and ignore any trailing unit text.
5. **Extract timestamp**: Use `resource.effectiveDateTime` if present; otherwise fall back to `resource.issued`.
6. **Return**: `[numeric_value, timestamp]`.
7. **Missing data**: If no entries match the criteria, return `[-1]` (a single‑element array with sentinel).

**Pattern 2: Fallback / verification rule**
- If the selected entry lacks `valueQuantity` and `valueString` cannot be parsed, treat it as missing and return `[-1]`.
- If the timestamp is missing, still return the numeric value with `null` timestamp, but log a warning (the agent can still decide based on value alone).

**Pattern 3: Formatting rule for downstream decisions**
- When the task includes a conditional order, compare the extracted numeric value against the clinical threshold *before* constructing any POST body.
- Example: `if value < 1.5 then POST ServiceRequest for IV magnesium`.

## Example Application
**Task:** "Check patient S1023381's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S1023381&date=ge2023-11-12T10:15:00+00:00`
2. Bundle contains three entries; sort by `effectiveDateTime` → newest is `2023-11-13T08:20:00+00:00` with `valueQuantity.value = 1.2`.
3. Extract `[1.2, "2023-11-13T08:20:00+00:00"]`.
4. Compare `1.2 < 1.5` → low, so construct:
   ```json
   {
     "resourceType": "ServiceRequest",
     "status": "active",
     "intent": "order",
     "code": {"coding":[{"system":"http://www.nlm.nih.gov/research/umls","code":"308182","display":"Magnesium sulfate IV"}]},
     "subject": {"reference":"Patient/S1023381"},
     "authoredOn": "2023-11-13T10:15:00+00:00"
   }
   ```
5. POST the ServiceRequest and FINISH with the order confirmation.

**If no recent observation:** the GET returns an empty bundle → return `[-1]` and FINISH with no order.

## Success Indicators
- The FINISH output contains a numeric value and an ISO‑8601 timestamp (or `[-1]`).
- Subsequent conditional logic (ordering) is triggered only when a numeric value is present.
- No free‑text placeholder strings appear in the answer.

## Failure Indicators
- FINISH returns a string message instead of `[value, timestamp]`.
- The returned array is empty or contains non‑numeric elements.
- The sentinel `-1` is omitted when no observation exists.
- The selected observation is older than the required window but still used.
