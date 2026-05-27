---
description: "Guarantee FINISH returns a JSON list **only** for tasks that contain\
  \ an explicit conditional decision about ordering a medication, lab, imaging, or\
  \ service. The rule now activates only when the task text includes both an ordering\
  \ verb *and* a conditional cue (e.g., \"if\", \"when\", \"unless\", \"no value\"\
  , \"low\", \"high\", \"threshold\", \"below\", \"above\"). This prevents the skill\
  \ from interfering with straightforward ordering tasks such as referrals, which\
  \ expect a free\u2011text or other payload."
name: enforce_list_output_on_conditional_order_tasks
provenance:
  action: ADD
  epoch: 4
  fixes: 11
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task9_9
  - task5_16
  - task9_27
  - task3_17
  - task9_14
  - task10_16
  - task4_28
  - task9_1
  - task10_12
  - task3_27
  update_cycle: 0
tags: []
version: 1
---

# Enforce List Output on Conditional Order Tasks (Narrowed)

## Purpose
Ensure that `FINISH` is called with a JSON array **only** for tasks that require a conditional decision (e.g., "if low, then order magnesium"). For plain ordering tasks (no conditional language), the skill does nothing, preserving the original expected payload format.

## When to Activate
Activate this skill **iff** the task description satisfies **both** of the following:
1. Contains an ordering verb or noun such as "order", "request", "place a lab", "prescribe", "refer", etc.
2. Contains at least one conditional cue word/phrase, e.g.:
   - "if", "when", "unless"
   - "no value", "no record", "not recorded"
   - "low", "high", "below", "above", "threshold", "greater than", "less than"
   - "only if", "provided that", "in case of"

If the task lacks any conditional cue, the skill **does not** modify the response.

## Normalisation Rules (applies only after activation)
1. **No order required** → `FINISH([])` (empty list).
2. **Order required** → `FINISH(["<short_token>"])` where `<short_token>` is a concise, machine‑readable identifier (e.g., `"order_magnesium_iv"`).
3. **Error handling** – if an internal error occurs, propagate the error **outside** the list (e.g., `FINISH({"error": "..."})`) or raise an exception; do **not** place free‑text error messages inside a list.

## Guard Clause (to avoid regressions)
```python
def should_enforce(task_text: str) -> bool:
    ordering_keywords = ["order", "request", "prescribe", "refer", "place a lab", "order lab", "order test"]
    conditional_cues = ["if", "when", "unless", "no value", "no record", "not recorded",
                         "low", "high", "below", "above", "threshold",
                         "greater than", "less than", "only if", "provided that", "in case of"]
    has_order = any(k in task_text.lower() for k in ordering_keywords)
    has_cond = any(c in task_text.lower() for c in conditional_cues)
    return has_order and has_cond
```
Only when `should_enforce` returns `True` does the skill rewrite the payload to a list.

## Example (still valid)
**Task:** "Check patient S1023381's last serum magnesium level within last 24 h. *If low*, then order replacement IV magnesium. *If no magnesium level recorded*, don't order anything."
- Detection: ordering verb + conditional cue → enforce.
- Decision → no recent value → `FINISH([])`.

## Non‑conditional Example (no enforcement)
**Task:** "Order orthopedic surgery referral for patient S6549951. Include the free‑text ..."
- Detection: ordering verb present, but **no** conditional cue → `should_enforce` returns `False`.
- The agent proceeds with its original logic (e.g., returning a success message or resource ID) and the skill does not intervene, preventing the regression observed in `task8_26`.

## Success Indicators
- `FINISH` receives a JSON array **only** for tasks that matched the conditional pattern.
- The array is either empty or contains only short identifier strings.
- Non‑conditional ordering tasks are untouched.

## Failure Indicators
- `FINISH` receives a plain string or free‑text sentence inside a list for a non‑conditional task.
- The list contains mixed types or full sentences for a conditional task.
- The guard clause incorrectly classifies a non‑conditional task as conditional.
