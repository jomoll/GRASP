---
description: Force execution of any provided bash script before answering when the
  task asks for a script that computes a numeric metric.
name: ensure_metric_bash_execution
provenance:
  action: MODIFY
  epoch: 3
  fixes: 4
  parent_version: 1
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - std-007-bootstrap-00001
  - std-005-new-00003
  - std-007-bootstrap-00026
  - std-007-bootstrap-00009
  - std-007-bootstrap-00075
  - std-007-bootstrap-00032
  - std-007-bootstrap-00034
  - std-007-bootstrap-00039
  - std-004-N41-00000
  - std-007-bootstrap-00003
  update_cycle: 1
tags: []
version: 2
---

# Execute Bash Script Before Answering

## Pattern Description
When a task explicitly asks you to *write* a bash script that calculates a numeric result (e.g., a count, sum, percentage, or any other metric), the correct workflow is to **execute the script first**, capture its stdout, and then return that captured value with `answer_action`. Returning the script itself as the answer violates the metric‑execution contract and leads to `script_returned_without_execution` failures. This skill enforces a two‑step pattern: **run → capture → answer**, ensuring the metric is derived from the live environment rather than being echoed back as code.

## When to Use This Skill
- The instruction contains phrases like **"write a bash script"**, **"bash script that"**, **"script to count"**, **"script to compute"**, or **"calculate the total/number of"** followed by a metric description.
- The expected answer is a **single integer or numeric value**, not a script body.
- The task does not request the script source as the final output (i.e., it asks for the result of the script).

## Common Failure Patterns
- Returning the script source in `answer_action` instead of executing it.
- Skipping `bash_action` entirely and directly answering with a placeholder.
- Executing the script but then embedding the raw command string in the answer instead of the numeric stdout.
- Using `finish_action` or plain text when a numeric `answer_action` is required.

## Recommended Patterns
**Pattern 1: Detect script‑required metric task**
1. In the *Think* step, scan the instruction for the trigger phrases above.
2. If detected, **do not** construct `answer_action` yet.
3. Immediately issue a `bash_action` with the **exact script** the instruction asks for.
4. Capture the stdout from the observation.

**Pattern 2: Validate and answer**
1. Verify the captured output is a non‑empty numeric string (use regex `^[0-9]+(\.[0-9]+)?$`).
2. If valid, call `answer_action({"answer": "<captured_value>"})`.
3. If not numeric (e.g., script printed extra text), trim to the first numeric token or re‑run with a more precise command.

**Pattern 3: Fallback**
- If the script execution fails (non‑zero exit code or no output), fall back to a minimal one‑liner that reproduces the metric (e.g., use `ps -e --no-headers | wc -l` for process count) and answer with that result.

## Example Application
**Task:** "Write a bash script that counts all active processes containing 'bash' in their command name and returns the count as an integer."

**Wrong trajectory (failure):**
1. *Think*: Need to provide the script.
2. *Act*: `answer_action({"answer": "#!/bin/bash\ncount=$(ps -e | grep bash | wc -l)\necho \"$count\""})`
3. *Obs*: None (no execution).
4. *Think*: End.
   → Failure: script returned without execution.

**Correct trajectory (skill applied):**
1. *Think*: Instruction asks for a bash script that computes a metric → trigger skill.
2. *Act*: `bash_action({"script": "#!/bin/bash\ncount=$(ps -e | grep bash | wc -l)\necho $count"})`
3. *Obs*: The OS returns `12`.
4. *Think*: Output is numeric, ready to answer.
5. *Act*: `answer_action({"answer": "12"})`
   → Success.

## Success Indicators
- The agent issues a `bash_action` **before** any `answer_action` when the trigger phrases are present.
- The observation from `bash_action` contains a single numeric string.
- The final `answer_action` payload includes that exact number and no script text.

## Failure Indicators
- `answer_action` contains script code or non‑numeric text.
- No `bash_action` is observed despite the task requesting a script‑based metric.
- The numeric answer is missing or malformed (e.g., extra whitespace, error messages).
