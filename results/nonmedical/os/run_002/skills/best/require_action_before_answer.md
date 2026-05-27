---
description: Force a bash_action (or other tool) before any answer_action when the
  task asks for a concrete system value
name: require_action_before_answer
provenance:
  action: ADD
  epoch: 1
  fixes: 0
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - std-007-bootstrap-00026
  - std-007-bootstrap-00004
  - std-005-new-00003
  - std-007-bootstrap-00000
  - std-007-bootstrap-00006
  - std-007-bootstrap-00065
  - std-007-bootstrap-00055
  - std-007-bootstrap-00007
  - std-004-N41-00000
  - std-005-new-00000
  update_cycle: 1
tags:
- count
- total
- number
- size
- lines
- exists
- path
- processes
- directories
- files
- lines of code
version: 1
---

# Require Action Before Answer

## Pattern Description
When the instruction asks for a concrete value that can only be obtained from the operating system (e.g., counts of files, existence of a path, total size, number of processes, lines of code, etc.), the agent must first run an appropriate `bash_action` (or other tool) to retrieve the data before issuing `answer_action`. This prevents the agent from guessing or answering without evidence, which is the primary failure mode observed as **no_actions_executed**.

## When to Use This Skill
- The task asks *how many*, *total*, *count*, *number of*, *size of*, *exists*, *path of*, *lines of code*, *processes*, or any other quantitative system property.
- The instruction contains keywords such as `how many`, `total`, `count`, `number of`, `size`, `lines`, `exists`, `path`, `processes`, `directories`, `files`, `lines of code`.
- No prior `bash_action` (or `python_action`, etc.) has been executed in the current turn.

## Common Failure Patterns
- Directly calling `answer_action` with a guessed value.
- Responding with natural‑language text instead of a JSON `answer_action` payload.
- Using a command that does not actually produce the required metric (e.g., `ls` then manual counting).

## Recommended Patterns
**Pattern 1: Detect the need for a system query**
1. Scan the instruction for any of the trigger keywords listed above.
2. Decide which OS metric is required.
3. Formulate a minimal, non‑truncating command that returns the exact number or string.
4. Execute the command with `bash_action`.
5. Capture the output and, if necessary, trim whitespace.
6. Call `answer_action` with the captured value.

**Pattern 2: Fallback if the primary command fails or returns empty**
- If the first command errors or returns an empty string, try an alternative command that achieves the same goal (e.g., use `find … -printf "%s\n"` instead of `wc -l`).
- If all attempts fail, return `answer_action` with a clear error message like `"Unable to determine the requested value"` rather than guessing.

**Pattern 3: Answer formatting**
- The payload must be exactly `{"answer": "<value>"}` where `<value>` is the raw string output of the command (no extra wording, no units unless the task explicitly asks for them).

## Example Application
**Task:** "How many `.py` files are in the directory `codebase` and all its subdirectories?"

**Wrong trajectory (fails – no action executed):**
1. **Think:** The user wants a count, I can guess it's 5.
2. **Act:** `answer_action({"answer": "5"})`
3. **Observation:** None (no tool call).
4. **Result:** Failure – *no_actions_executed*.

**Correct trajectory (skill applied):**
1. **Think:** The question asks for a concrete file count → trigger.
2. **Act:** `bash_action({"script": "find codebase -type f -name '*.py' | wc -l"})`
3. **Observation:** `42`
4. **Think:** Use the observed number as the answer.
5. **Act:** `answer_action({"answer": "42"})`
6. **Observation:** Agent returns the correct JSON payload.

## Success Indicators
- The first non‑thinking action in the turn is a `bash_action` (or other tool) that directly addresses the metric.
- The final `answer_action` payload contains exactly the value observed from the tool.
- No intermediate `answer_action` is emitted before a tool call.

## Failure Indicators
- An `answer_action` is sent before any tool call.
- The answer includes explanatory text or units that were not requested.
- The command used does not directly produce the required numeric/string value (e.g., `ls` followed by manual counting).
