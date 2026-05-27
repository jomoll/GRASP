---
description: Enforce concise FINISH output that contains only the exact answer elements
  required by the task.
name: strict_answer_format
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 0
  fixes_unused: 5
  probe_score_unused: -2
  regressions_unused: 2
  triggering_sample_ids:
  - task4_26
  - task9_28
  - task2_9
  - task5_17
  - task9_3
  - task4_23
  - task9_27
  - task2_15
  - task2_6
  - task10_24
  update_cycle: 1
tags: []
version: 1
---

# Strict Answer Format

## Pattern Description
You must ensure that the final `FINISH` call returns **only** the data explicitly requested by the task, formatted exactly as the specification demands. No explanatory sentences, no extra context, and no additional array elements beyond what the task asks for. This pattern applies to any task where the answer is expected to be a simple value (string, number, or a short list) wrapped in a JSON array.

## When to Use This Skill
- When a task asks for a single identifier, measurement, or flag (e.g., MRN, latest lab value, `-1` for missing data).
- When a task requests a list of values but does not ask for narrative commentary.
- Whenever the agent is about to emit `FINISH([...])` and the surrounding instruction does not explicitly require prose.

## Common Failure Patterns
- `FINISH(["Patient S123's potassium is 4.7 mmol/L, no action needed."])` – extra explanatory text inside the array.
- `FINISH(["5.2%", "Recorded on 2022-08-09."])` – separate strings when a single combined string is required.
- `FINISH(["Blood pressure 118/77 mmHg recorded.", "Additional note."])` – more than the required element(s).
- Returning a plain string without the surrounding array, e.g., `FINISH("S123")`.

## Recommended Patterns
**Pattern 1: Identify the exact answer shape**
1. Parse the task description to determine the required output type (single string, number, or list).
2. Extract only the needed field(s) from the FHIR response.
3. Construct a JSON array containing **exactly** those field(s) in the order specified.
4. Do **not** add any extra wording, units (if already part of the value), or commentary.

**CORRECT**: `FINISH(["S6200102"])`
**WRONG**: `FINISH(["The MRN is S6200102."])`

**Pattern 2: When multiple values are required**
1. List each required value as a separate element in the array, preserving order.
2. Do not concatenate values into a single string unless the task explicitly asks for it.

**CORRECT**: `FINISH(["5.2%", "2022-08-09"])`
**WRONG**: `FINISH(["5.2% recorded on 2022-08-09"])`

**Pattern 3: Fallback verification**
- After constructing the array, double‑check that the number of elements matches the task's specification. If it does not, abort and log a warning.

## Example Application
**Task:** "What’s the MRN of the patient with name Kevin Vasquez and DOB of 1953-11-19? If the patient does not exist, the answer should be \"Patient not found\"."

**Step‑by‑step:**
1. Issue `GET /Patient?family=Vasquez&given=Kevin&birthdate=1953-11-19`.
2. From the Bundle, extract the patient identifier (`S6200102`).
3. The task expects a single string inside an array.
4. Emit `FINISH(["S6200102"])`.

**CORRECT output:** `FINISH(["S6200102"])`
**WRONG output:** `FINISH(["Patient S6200102 found."])`

## Success Indicators
- The `FINISH` payload contains exactly the number and type of elements the task description demands.
- No extra words, punctuation, or explanatory sentences appear inside the array.
- Unit tests that compare the agent's output to the expected JSON array pass.

## Failure Indicators
- The `FINISH` array includes narrative text or more elements than required.
- The output is a plain string or object instead of a JSON array.
- Unit tests flag a mismatch between expected and actual element count or content.
