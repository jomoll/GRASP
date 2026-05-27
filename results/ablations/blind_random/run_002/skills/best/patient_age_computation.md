---
description: Make age answers plain integers, not string arrays
name: patient_age_computation
provenance:
  action: MODIFY
  blind_select: random
  epoch: 1
  fixes_unused: 7
  parent_version: 1
  probe_score_unused: 2
  regressions_unused: 1
  triggering_sample_ids:
  - task10_27
  - task1_16
  - task4_26
  - task10_12
  - task2_22
  - task10_13
  - task10_18
  - task1_15
  - task4_10
  - task3_19
  update_cycle: 1
tags: []
version: 2
---

# Patient Age Computation

## Pattern Description
You must compute a patient’s age from the `birthDate` element of a `Patient` resource using the current time supplied in the task context. The result is a **plain integer** representing whole years (rounded down). This skill is used whenever a task asks for “the age of the patient …” and the answer type is defined as a numeric scalar.

## When to Use This Skill
- When the instruction is *"What’s the age of the patient …"* or any equivalent phrasing.
- The task context provides a current timestamp (e.g. `2023-11-13T10:15:00+00:00`).
- The expected answer format is a single integer, not a JSON array or quoted string.

## Common Failure Patterns
- Returning `FINISH(["82"])` – age wrapped in an array and quoted as a string.
- Returning `FINISH([82])` – array instead of scalar.
- Using the wrong field (`age` from a custom extension) instead of calculating from `birthDate`.

## Recommended Patterns
**Pattern 1: Core age calculation**
1. Issue a `GET` request for the patient using the MRN or identifier.
2. From the returned `Bundle`, locate the `Patient` entry and read `birthDate` (ISO‑8601 date string).
3. Parse the task‑provided current time (also ISO‑8601).
4. Compute the difference in years, rounding down (e.g., using floor on the year‑difference after adjusting for month/day).
5. Call `FINISH(<age>)` where `<age>` is a bare integer (e.g., `FINISH(82)`).

**CORRECT**: `FINISH(82)`
**WRONG**: `FINISH(["82"])` or `FINISH([82])`

**Pattern 2: Fallback for missing birthDate**
- If the `Patient` resource lacks a `birthDate`, call `FINISH(-1)` to indicate unknown age.

**Pattern 3: Output formatting**
- Do not wrap the integer in quotes or brackets.
- Do not add any explanatory text; the answer must be exactly the integer.

## Example Application
**Task:** "What's the age of the patient with MRN of S6537563?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S6537563`
2. Extract `birthDate` from the `Patient` entry, e.g. `1941-04-12`.
3. Current time from context: `2023-11-13T10:15:00+00:00`.
4. Compute age: 2023‑1941 = 82 (birthday already passed this year → 82).
5. `FINISH(82)`

## Success Indicators
- The final agent output is exactly `FINISH(<integer>)` with no surrounding brackets or quotes.
- The integer matches the floor of the year‑difference calculation.

## Failure Indicators
- Output contains `[` or `]` or surrounding quotes.
- The agent returns a string representation of the number.
- The agent includes any extra text or units.
