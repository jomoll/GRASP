---
description: "Extract numeric or boolean values **only** when the task explicitly\
  \ asks for a primitive answer (a single number, a boolean, or a sentinel numeric\
  \ value) **and** the most recent API call was a GET that returned a FHIR Bundle.\
  \ For all other tasks (e.g., retrieving identifiers, creating resources, or posting\
  \ free\u2011text notes) the skill does nothing, allowing the agent to finish normally."
name: use_fhir_response_for_answer
provenance:
  action: MODIFY
  epoch: 1
  fixes: 17
  parent_version: 1
  probe_score: 13
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task10_17
  - task4_28
  - task9_28
  - task9_22
  - task8_3
  - task5_17
  - task8_19
  - task10_20
  - task10_27
  update_cycle: 0
tags: []
version: 2
---

# use_fhir_response_for_answer (narrowed)

## Guard Conditions
1. **Instruction cue** – The task description must contain one of the following cues indicating a primitive answer is required:
   - "answer should be a single number"
   - "answer should be a number"
   - "return a number"
   - "return a boolean"
   - "true/false"
   - "order needed" / "no order needed"
   - "sentinel value" (e.g., "-1 if not found")
   - any phrase that explicitly states the expected output type is numeric or boolean.
2. **API context** – The most recent API call performed by the agent must be a **GET** request whose response is a FHIR `Bundle` (i.e., `resourceType == "Bundle"`). If the last call was a POST/PUT/PATCH or the response is not a Bundle, the skill does **not** run.

If either guard fails, the skill aborts and the agent proceeds without emitting a FINISH payload.

## Extraction Logic (executed only when both guards are satisfied)
1. Locate the first entry in `Bundle.entry` that matches the requested code or identifier (the exact matching logic is left to the agent’s existing code – this skill only assumes the correct entry is already identified).
2. Read the numeric value from `resource.valueQuantity.value` (or from `resource.valueQuantity` if the value is directly present).
3. If a unit conversion is required (detected by comparing `resource.valueQuantity.unit` with the unit requested in the instruction), apply the known conversion factor (e.g., `mmol/L → mg/dL`).
4. Store the resulting primitive in a variable `extracted_val`.
5. **Conditional handling** – If the bundle has `total: 0` or no matching entry, set `extracted_val` to the sentinel value defined by the instruction (commonly `-1` or `null`).
6. Emit the final answer **without any free‑text**:
   - For numeric answers: `FINISH([extracted_val])`
   - For boolean answers: `FINISH([true])` or `FINISH([false])`
   - For sentinel cases: `FINISH([sentinel])`

## Example (still valid)
**Task:** "What’s the most recent magnesium level in mg/dL? Answer should be a single number, and -1 if no recent measurement."
- GET ...
- Bundle contains `valueQuantity.value = 2.2` and `unit = "mg/dL"` → `extracted_val = 2.2`
- `FINISH([2.2])`

## Why this revision fixes regressions
- **Task 1 (MRN lookup)** does not contain a numeric‑answer cue, so the guard prevents the skill from running; the agent can return the required string "Patient not found".
- **Task 8 (ServiceRequest with free‑text note)** is a POST operation; the guard on the last API call being a GET stops the skill from interfering, preserving the correct FINISH([]).
- **Task 3 (record BP)** also involves a POST and no numeric‑answer cue, so the skill is bypassed, allowing the agent to finish with an empty array as expected.

## Tags
[]
