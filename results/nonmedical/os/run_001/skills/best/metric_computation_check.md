---
description: Verify that numeric answers exactly match the output of the preceding
  bash_action and correspond to the metric requested in the task.
name: metric_computation_check
provenance:
  action: MODIFY
  epoch: 3
  fixes: 3
  parent_version: 1
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - std-004-Q19-00000
  - std-007-bootstrap-00084
  - std-007-bootstrap-00071
  - std-007-bootstrap-00065
  - std-007-bootstrap-00020
  - std-007-bootstrap-00061
  - std-004-N37-00000
  - std-007-bootstrap-00025
  - std-007-bootstrap-00038
  - std-007-bootstrap-00066
  update_cycle: 0
tags: []
version: 2
---

# Metric Computation Verification

## Pattern Description
This skill ensures that whenever a task asks for a numeric metric (counts, sizes, sums, etc.), the agent does not fabricate or mis‑interpret the result. After a `bash_action` is executed, the agent must capture the raw stdout, trim whitespace, and compare it to the value placed in the subsequent `answer_action`. If the two differ, the agent must either correct the answer or re‑run an appropriate command that directly yields the required metric. This prevents the dominant failure mode where the agent reports an arbitrary integer that does not reflect the command output.

## When to Use This Skill
- When the task instruction contains words like **count**, **total**, **sum**, **number of**, **how many**, **size**, **lines**, **words**, **characters**, **files**, **directories**, **occurrences**, etc., indicating a numeric metric is expected.
- Immediately after a `bash_action` has been performed and before any `answer_action` is emitted.
- When the most recent `bash_action` produced a plain numeric output (or a single‑line output that can be parsed to a number).

## Common Failure Patterns
- Agent calls `answer_action` with a hard‑coded integer that does not equal the bash output (e.g., `answer_action({"answer": "10"})` while the bash output was `42`).
- Agent answers a different metric than requested (e.g., counting *files* but answering the number of *lines*).
- Agent returns a formatted string instead of a pure integer when the task asks for a number (e.g., `"10 files"`).
- Agent skips verification entirely and finishes with `finish_action` or plain text.

## Recommended Patterns
**Pattern 1: Capture and Verify Bash Output**
1. After a `bash_action`, store the raw stdout in a variable `bash_out`.
2. Trim leading/trailing whitespace: `metric=$(echo "$bash_out" | tr -d '\n' | xargs)`.
3. If `metric` matches the regular expression `^-?[0-9]+$`, proceed.
4. Before emitting `answer_action`, compare `metric` to the value you plan to send.
   - **If they match**, call `answer_action({"answer": "$metric"})`.
   - **If they differ**, re‑run a more direct command that yields the exact metric (e.g., use `find … -type f | wc -l` for file counts, `wc -l` for line counts, `grep -o "word" … | wc -l` for occurrences).

**Pattern 2: Fallback when Output Is Not a Simple Number**
- If the bash output contains multiple fields, extract the numeric column that corresponds to the requested metric using `awk` or `cut`.
- If no numeric output is produced, emit a helpful `answer_action` indicating inability to compute rather than guessing.

**Pattern 3: Answer Formatting Rule**
- Always send a *pure* integer string in the `answer` field. No units, no extra text.
- Example **CORRECT**: `answer_action({"answer": "42"})`
- Example **WRONG**: `answer_action({"answer": "42 files"})`

## Example Application
**Task:** "Count the total number of lines in all '.txt' files under `~/txt_problem` and return the result as an integer."

**Wrong trajectory (fails metric verification):**
1. **Think:** I need to count lines.
2. **Act:** `bash_action({"script": "find ~/txt_problem -type f -name \"*.txt\" -exec cat {} + | wc -l"})`
3. **Obs:** Output = `58`
4. **Think:** I will answer 10 (incorrect).
5. **Act:** `answer_action({"answer": "10"})`
   *Metric verification skill triggers – detected mismatch (58 vs 10) and forces correction.*

**Correct trajectory (skill applied):**
1. **Think:** I need to count lines.
2. **Act:** `bash_action({"script": "find ~/txt_problem -type f -name \"*.txt\" -exec cat {} + | wc -l"})`
3. **Obs:** Output = `58`
4. **Think:** Store output, trim, verify it is numeric → `metric=58`.
5. **Act:** `answer_action({"answer": "58"})`
   *The answer matches the captured metric, so the skill is satisfied.*

## Success Indicators
- The `answer_action` payload is a single integer that exactly equals the trimmed stdout of the most recent `bash_action`.
- No extra text or units are present in the answer.
- The agent does not emit `finish_action` before the verification step.

## Failure Indicators
- `answer_action` contains a value that differs from the captured bash output.
- The agent answers with formatted text (e.g., "58 lines") instead of a plain integer.
- The skill was bypassed and the agent directly emits `answer_action` without any preceding `bash_action` when a metric is required.
