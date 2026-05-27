---
description: Suppresses extraneous lab value summaries when the task only requires
  action if abnormal.
name: suppress_unnecessary_lab_report_when_no_action_needed
provenance:
  action: ADD
  epoch: 0
  fixes: 6
  probe_score: 6
  regressions: 0
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  update_cycle: 1
tags:
- lab
- reporting
- suppression
- conditional_action
- potassium
- magnesium
version: 1
---

# Suppress Unnecessary Lab Report When No Action Needed

## Pattern Description

When a task instructs you to check a lab value (such as potassium or magnesium) and only take action if the value is abnormal (e.g., low), you must avoid generating a summary or report of the lab value if no action is required. The correct behavior is to take no action (or only state that no order will be placed if explicitly required), not to generate a narrative summary of normal results. This prevents clutter and ensures the agent only acts when intervention is needed.

This pattern applies to tasks where the instruction is conditional: "If low, then order replacement; if not, do nothing." Generating a summary of normal results is extraneous and can confuse downstream systems or users expecting only actionable outputs.

## When to Use This Skill

- When the instruction is to check a lab value and only act (e.g., order replacement) if the value is abnormal (e.g., low).
- When the instruction explicitly says to do nothing if the lab value is normal or not found.
- When the task does not request a summary or report of the lab value if no action is needed.
- When the only required output is an order if the threshold is crossed, or silence otherwise.

## Common Failure Patterns

- Returning a narrative summary of the lab value when it is normal (e.g., "The last serum magnesium level is 2.2 mg/dL, which is normal. No IV magnesium replacement is needed.").
- Including statements like "No replacement is needed" or "No action required" when the instruction does not request such confirmation.
- FINISHing with an array containing a summary string instead of an empty array or no output.

## Recommended Patterns

**Pattern 1: Action Only When Abnormal**
1. Retrieve the relevant lab value using GET /Observation with the correct code, patient, and date parameters.
2. If the lab value is below the threshold, proceed to order the replacement as instructed.
3. If the lab value is normal or above the threshold, do not generate any summary or report. FINISH with an empty array or no output.

CORRECT: `FINISH([])`
WRONG:   `FINISH(["The last serum magnesium level is 2.2 mg/dL, which is normal. No IV magnesium replacement is needed."])`

**Pattern 2: No Lab Value Found**
1. If no lab value is found in the specified time window, and the instruction says to do nothing, FINISH with an empty array or no output.
2. Do not generate a summary stating that no value was found unless the instruction explicitly requests it.

**Pattern 3: Explicit Action Required**
1. If the instruction requests confirmation that no order will be placed, return only the minimal confirmation (e.g., "No IV magnesium replacement will be ordered.").
2. Do not include the lab value or additional narrative unless requested.

## Example Application

**Task:** "Check patient S3057899's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step-by-step:**

1. Issue GET /Observation?code=MG&patient=S3057899&date=ge2023-11-12T10:15:00+00:00
2. Extract the most recent value and compare to the low threshold.
3. If value is normal (e.g., 2.2 mg/dL), FINISH with an empty array.
4. If value is low, proceed to order IV magnesium and FINISH with confirmation of the order.

CORRECT output: `FINISH([])`
WRONG output:   `FINISH(["The last serum magnesium level for patient S3057899 within the past 24 hours is 2.2 mg/dL (drawn at 2023-11-12T23:31:00+00:00), which is normal. No IV magnesium replacement is needed."])`

## Success Indicators

- No output or only an order confirmation is returned when the lab value is normal and no action is required.
- No narrative summary of normal lab values is generated unless explicitly requested.
- FINISH is called with an empty array or only with order confirmation when appropriate.

## Failure Indicators

- FINISH includes a summary of the lab value when it is normal and no action is required.
- FINISH includes statements like "No replacement is needed" or "No action required" when not requested.
- The output contains extraneous narrative or explanation in cases where the instruction is to act only if abnormal.
