---
description: Ensure electrolyte replacement skill returns only concise decision strings
  without extra explanatory text
name: electrolyte_replacement_service_request
provenance:
  action: MODIFY
  blind_select: random
  epoch: 1
  fixes_unused: 0
  parent_version: 1
  probe_score_unused: 0
  regressions_unused: 6
  triggering_sample_ids:
  - task4_7
  - task2_30
  - task9_22
  - task4_4
  - task2_22
  - task9_1
  - task4_28
  - task2_26
  - task2_1
  - task2_14
  update_cycle: 1
tags: []
version: 2
---

# Electrolyte Replacement ServiceRequest Concise Output

## Pattern Description
You must generate a ServiceRequest for electrolyte replacement **only** when the most recent lab value is below the therapeutic threshold. The agent’s final answer must be a minimal, single‑sentence decision wrapped in a `FINISH([...])` array. No extra narrative, values, or explanations are allowed. This pattern applies to any electrolyte (e.g., potassium, magnesium) where the task asks to check a recent level and conditionally order replacement.

## When to Use This Skill
- When a task says *"Check patient X's most recent [electrolyte] level. If low, then order replacement according to dosing instructions."*
- When the task also asks to pair the order with a follow‑up lab (e.g., a repeat serum level the next day).
- When the task expects a **single** concise response indicating either that a replacement was ordered or that no action is needed.

## Common Failure Patterns
- Returning a full sentence that includes the numeric value and threshold, e.g., `"4.7 mmol/L (most recent) is above the 3.5 mmol/L threshold; no potassium replacement ordered."`
- Adding explanatory text such as "value within normal range" or "above threshold".
- Including both the decision and the reason in the same output string.

## Recommended Patterns
**Pattern 1: Core decision logic**
1. **Extract the most recent observation** for the requested electrolyte (`code` parameter) from the Bundle response.
2. Read `valueQuantity.value` (numeric) and `valueQuantity.unit`.
3. Compare the numeric value to the therapeutic threshold defined for that electrolyte (e.g., potassium < 3.5 mmol/L, magnesium < 1.5 mg/dL).
4. **If below threshold**:
   - POST a `ServiceRequest` with the appropriate NDC/code for the replacement medication.
   - FINISH with a single short phrase, e.g., `FINISH(["Potassium replacement ordered for patient S123456"])`.
5. **If not below threshold**:
   - Do **not** create a ServiceRequest.
   - FINISH with a single short phrase, e.g., `FINISH(["Potassium level normal; no replacement ordered"])`.

**Pattern 2: Follow‑up lab pairing (optional)**
- After ordering replacement, also POST a `ServiceRequest` for a repeat serum electrolyte level at the requested future time (e.g., next day 08:00).
- The FINISH output still remains a single decision phrase; the follow‑up request is a side‑effect, not part of the answer string.

**Pattern 3: Formatting rule**
- The FINISH payload must be a JSON array containing **exactly one string**.
- Do **not** include brackets, parentheses, or extra commas inside the string.
- Example of correct output: `FINISH(["Magnesium replacement ordered for patient S6541353"])`.
- Example of WRONG output: `FINISH(["Magnesium level 2.0 mg/dL is within normal range; no replacement ordered."])`.

## Example Application
**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=K&patient=S6474456`.
2. From the returned Bundle, locate the entry with the highest `effectiveDateTime`.
3. Extract `valueQuantity.value` (e.g., `3.2`) and compare to threshold `3.5`.
4. Since `3.2 < 3.5`, POST a `ServiceRequest` for potassium replacement (using the provided NDC).
5. POST a second `ServiceRequest` for a repeat potassium level at `2023-11-14T08:00:00+00:00`.
6. FINISH with: `FINISH(["Potassium replacement ordered for patient S6474456"])`.

## Success Indicators
- The agent issues the correct GET request, creates the ServiceRequest(s) when needed, and calls FINISH with a one‑element array containing only the short decision phrase.
- No numeric values, thresholds, or explanatory clauses appear inside the FINISH string.

## Failure Indicators
- FINISH contains a full sentence with values or reasons.
- The FINISH array has more than one element or includes extra punctuation inside the string.
- The agent creates a ServiceRequest but still returns a verbose answer.
