---
description: "Detect conditional ordering cues regardless of word order and case to\
  \ suppress raw lab\u2011value list output"
name: enforce_list_output_on_conditional_order_tasks
provenance:
  action: MODIFY
  epoch: 6
  fixes: 4
  parent_version: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_14
  - task10_16
  - task9_3
  - task3_3
  - task9_27
  - task9_11
  - task10_10
  - task10_13
  update_cycle: 0
tags: []
version: 2
---

# Enforce List Output on Conditional Order Tasks

## Pattern Description
You must ensure that the agent only returns a JSON list of values **when** the task explicitly combines an ordering intent with a conditional decision (e.g., "if low"). The detection must be case‑insensitive and work no matter whether the ordering verb appears before or after the conditional cue. This prevents the agent from mistakenly outputting raw lab values for tasks that require a conditional order.

## When to Use This Skill
- When a task asks to *check* a lab/observation **and** *order* a medication, lab, imaging, or service **only if** a condition is met (e.g., "If low, then order potassium").
- The task description contains any ordering verb (`order`, `prescribe`, `administer`, `give`) **and** any conditional cue (`if`, `when`, `unless`, `low`, `high`, `threshold`, `below`, `above`, `no value`).
- The ordering verb may appear before or after the conditional cue, and may be part of a longer phrase (e.g., "order replacement potassium").

## Common Failure Patterns
- Ordering verb appears **after** the conditional cue, so the original regex misses the pair.
- Mixed‑case words (`If Low`, `ORDER`) cause case‑sensitive matching to fail.
- The ordering verb is part of a longer token (`order replacement`) and is not matched by a strict word‑boundary pattern.
- Tasks that are simple referrals contain an ordering verb but **no** conditional cue, yet the skill incorrectly blocks them.

## Recommended Patterns
**Pattern 1: robust conditional‑order detection**
1. Convert the entire task description to lower‑case.
2. Search for any ordering verb using the regex `\b(order|prescribe|administer|give)\b`.
3. Search for any conditional cue using the regex `\b(if|when|unless|low|high|threshold|below|above|no\s+value)\b`.
4. If **both** matches are found **anywhere** in the text, activate the skill (i.e., suppress raw list output and expect an order action).
5. If only one side is present, do **not** activate – allow normal FINISH behavior.

**Pattern 2: fallback verification**
- After detecting a conditional order, verify that the agent has performed a POST/PUT to create the appropriate `ServiceRequest` or `MedicationRequest` before calling FINISH. If no such API call is observed, raise a warning and abort the FINISH.

**Pattern 3: output formatting rule**
- When the skill is active, the FINISH payload must **not** contain a plain list of observation values. Instead, it should return either an empty list (if no order is needed) or a confirmation object from the order creation skill.

## Example Application
**Task:** "Check patient S123456's most recent potassium level. If low, then order replacement potassium."

**Step‑by‑step:**
1. Lower‑case description → "check patient s123456's most recent potassium level. if low, then order replacement potassium."
2. Detect ordering verb → matches "order".
3. Detect conditional cue → matches "if" and "low".
4. Both present → activate skill.
5. Agent must issue a GET for the potassium Observation, evaluate the value, and **only if** the value is below the low threshold perform a POST `ServiceRequest` for potassium replacement.
6. FINISH should return either `[]` (no order) or the order confirmation payload, never `[value, datetime]`.

**CORRECT output (no low value):** `FINISH([])`
**WRONG output (raw lab value):** `FINISH([3.9, "2023-11-12T13:35:00+00:00"])`

## Success Indicators
- FINISH never returns a plain list of observation values for tasks that contain both an ordering verb and a conditional cue.
- The agent performs a POST/PUT to create the appropriate order before calling FINISH.
- Logs show both regex matches were found regardless of word order or case.

## Failure Indicators
- FINISH returns a raw observation list despite the task containing "if low" and "order".
- No order‑creation API call is observed when the conditional is met.
- The skill fails to trigger when the ordering verb is part of a longer phrase (e.g., "order replacement").
