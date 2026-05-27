---
description: "Add explicit low\u2011threshold checks for potassium and magnesium before\
  \ creating replacement orders"
name: conditional_order_logic
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_16
  - task5_7
  - task9_27
  - task9_14
  update_cycle: 0
tags:
- order_logic
- thresholds
version: 3
---

# conditional_order_logic

## Pattern Description
You must only create a replacement order for electrolytes when the most recent lab value falls below a clinically defined low‑threshold. This prevents unnecessary orders and aligns with the task instruction "If low, then order replacement…". The skill centralises the threshold logic for potassium (K) and magnesium (MG) and couples it with the creation of the appropriate `ServiceRequest` resources.

## When to Use This Skill
- After a lab value has been extracted and normalised (using `concise_lab_value_output`).
- The task explicitly states a conditional order based on a "low" result.
- The agent is about to POST a `ServiceRequest` for potassium or magnesium replacement.

## Common Failure Patterns
- Ordering replacement even when the lab value is normal (e.g., `4.7 mmol/L` for potassium).
- Missing the second‑order pairing (e.g., a follow‑up serum potassium draw) because the first order was placed incorrectly.
- Using the wrong threshold (e.g., 4.0 mmol/L instead of 3.5 mmol/L for potassium).

## Recommended Patterns
**Pattern 1: low‑threshold decision rule**
1. Define thresholds: `K_LOW = 3.5` mmol/L, `MG_LOW = 1.7` mg/dL.
2. Parse the scalar lab result string produced by `concise_lab_value_output` to extract the numeric value.
3. Compare the numeric value to the appropriate threshold.
4. **If** the value < threshold, proceed to create the replacement `ServiceRequest` (using the NDC code supplied in the task context).
5. **Else**, skip order creation and simply `FINISH([])` or return the lab value.

**Pattern 2: paired follow‑up order**
- When ordering potassium replacement, also create a second `ServiceRequest` for a serum potassium draw scheduled for `task.context.now + 1 day` at `08:00`.
- Use the LOINC code `2823-3` for the draw and set `occurrenceDateTime` accordingly.

**Pattern 3: order confirmation**
- After successful POST(s), invoke `order_confirmation_output` to emit a concise confirmation string (e.g., `"Potassium replacement order created for patient S6550627."`).

## Example Application
**Task:** "Check patient S6550627's most recent potassium level. If low, then order replacement potassium and schedule a morning draw."

**Step‑by‑step:**
1. GET the potassium Observation and extract `"4.3 mmol/L"`.
2. `concise_lab_value_output` yields `FINISH(["4.3 mmol/L"])`.
3. Parse numeric part → `4.3`.
4. Compare to `K_LOW = 3.5`; since `4.3 >= 3.5`, **do not** POST any `ServiceRequest`.
5. Call `FINISH([])` (or return the lab value only).

**CORRECT behaviour:** No order is created; the agent finishes without a replacement order.
**WRONG behaviour (current):** The agent creates a potassium replacement `ServiceRequest` and a follow‑up draw despite the normal value.

## Success Indicators
- No `POST /ServiceRequest` is issued when the lab value is ≥ the low threshold.
- When the value is below threshold, exactly one replacement order (and optional follow‑up) is posted.
- The final `FINISH` contains either the lab value alone or a concise confirmation string, never both.

## Failure Indicators
- Replacement orders appear for normal or high electrolyte values.
- The agent posts duplicate or unnecessary follow‑up draws.
- Threshold values are hard‑coded incorrectly or omitted, leading to false positives.
