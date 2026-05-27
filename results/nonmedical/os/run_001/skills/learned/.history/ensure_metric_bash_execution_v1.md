---
description: Force a bash_action to compute simple numeric or yes/no metrics before
  answering.
name: ensure_metric_bash_execution
provenance:
  action: ADD
  epoch: 2
  fixes: 2
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - std-007-bootstrap-00065
  - std-004-Q49-00000
  - std-004-Q19-00000
  - std-004-N41-00000
  - std-007-bootstrap-00049
  - std-007-bootstrap-00019
  - std-007-bootstrap-00004
  - std-007-bootstrap-00027
  - std-004-Q30-00003
  - std-007-bootstrap-00030
  update_cycle: 1
tags:
- count
- number
- how many
- exists
- existence
- test
- integer
- yes/no
- path
- most recent
version: 1
---

# Ensure Required Bash Execution for Simple Metric Queries

## Pattern Description
You must recognize when a task asks for a single scalar result – a count, a size, an existence test, or a yes/no decision – and treat it as a *metric* request. Instead of guessing or answering directly, the agent must first run an appropriate Bash command that computes the exact value, capture its output, and then emit the result via `answer_action`. This prevents the dominant "no_actions_executed" failure where the agent finishes without any `bash_action`.

## When to Use This Skill
- The instruction contains phrases like **"how many", "number of", "count", "total", "paths in \$PATH", "most recent file", "exists", "is there", "test if", "determine if", "integer?"**.
- The expected answer is a single integer **or** the exact strings **"yes"** / **"no"** (case‑insensitive).
- No explicit script or multi‑step implementation is requested; the task is purely informational.

## Common Failure Patterns
- Returning a plain answer without any `bash_action` (e.g., `answer_action({"answer": "42"})`).
- Using `finish_action` or ending with free‑form text instead of `answer_action`.
- Guessing the metric (e.g., replying "yes" without checking the filesystem).
- Running an unrelated command that does not produce the required metric.

## Recommended Patterns
**Pattern 1: Detect and select the proper Bash command**
1. Scan the instruction for the keywords above.
2. Map the request to a concrete command:
   - *Count lines in a file*: `wc -l <file>`
   - *Count files of a type*: `find <dir> -type f -name "*.ext" | wc -l`
   - *Check existence*: `test -e <path> && echo yes || echo no`
   - *Test integer variable*: `[[ "$var" =~ ^-?[0-9]+$ ]] && echo yes || echo no`
   - *Count entries in $PATH*: `IFS=':'; count=0; for d in $PATH; do [ -d "$d" ] && ((count++)); done; echo $count`
   - *Most recent file (non‑recursive)*: `ls -1t <dir> | head -n1`
3. **Execute** the command with `bash_action`.

**Pattern 2: Parse the observation**
1. Receive the raw output from the OS.
2. Strip whitespace and newlines (`trim` the string).
3. Ensure the output matches the expected type (integer or "yes"/"no").
4. If parsing fails, fallback to a secondary safe command (e.g., repeat with `-print0` for `find`).

**Pattern 3: Emit the final answer**
- Call `answer_action` with a JSON payload containing only the scalar value, **no extra text**.
  - Correct: `answer_action({"answer": "42"})`
  - Wrong: `answer_action({"answer": "There are 42 files"})`

## Example Application
**Task:** "How many lines are there in /root/matrix.txt?"

**Wrong trajectory (fails)**
1. *Think*: The task asks for a line count, I can just answer.
2. *Act*: `answer_action({"answer": "123"})`
3. *Obs*: – (no observation, because no command was run)
4. *Think*: – (nothing to verify)
*Result*: No `bash_action` → failure.

**Correct trajectory (passes)**
1. *Think*: This is a line‑count metric. I need to run `wc -l`.
2. *Act*: `bash_action({"script": "wc -l /root/matrix.txt | awk '{print $1}'"})`
3. *Obs*: `123`
4. *Think*: The output is an integer, ready to answer.
5. *Act*: `answer_action({"answer": "123"})`
*Result*: Metric computed, answer correctly formatted.

## Success Indicators
- A `bash_action` appears **before** any `answer_action`.
- The `answer_action` payload contains only the scalar value.
- The observation from the `bash_action` is parsed and matches the expected type.

## Failure Indicators
- `answer_action` (or `finish_action`) is emitted without a preceding `bash_action`.
- The answer payload includes explanatory text or units.
- The selected command does not address the metric (e.g., `ls` when a count is required).
