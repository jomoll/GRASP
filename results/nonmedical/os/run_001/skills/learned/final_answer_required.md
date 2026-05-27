---
description: Force the agent to emit an answer_action with the computed result instead
  of ending with finish_action or plain text.
name: final_answer_required
provenance:
  action: ADD
  epoch: 0
  fixes: 2
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - std-007-bootstrap-00066
  - std-007-bootstrap-00039
  - std-001-stock-00002
  - std-007-bootstrap-00072
  - std-007-bootstrap-00004
  - std-004-N225-00000
  - std-007-bootstrap-00021
  - std-007-bootstrap-00049
  - std-007-bootstrap-00016
  - std-007-bootstrap-00014
  update_cycle: 0
tags:
- answer
- count
- integer
- output
- final
- result
version: 1
---

# Final Answer Required

## Pattern Description
When a task asks for a concrete result (e.g., a number, a path, a string) the agent must finish the episode by calling `answer_action` with a JSON payload that contains exactly the requested value under the key `answer`.  The agent should never end the episode with a `finish_action` or by emitting the answer as free‑form text.  This constraint prevents the dominant failure mode where the agent performs the required computation but forgets to return the answer in the prescribed protocol.

## When to Use This Skill
- The instruction explicitly says *"output the count as an integer"*, *"return an integer value"*, *"your answer should be a single number"*, or any wording that demands a concrete scalar answer.
- The task does **not** ask for a multi‑step report, a script file, or a description; it expects a single value.
- The agent has just performed a computation (e.g., `wc -l`, `find … | wc -l`, `grep … | wc -l`) and holds the result in a shell variable or has it in the tool output.

## Common Failure Patterns
- Calling `finish_action` after the computation instead of `answer_action`.
- Printing the result as normal assistant text (e.g., `The count is 42`).
- Omitting the JSON wrapper entirely, e.g., `answer: 42`.
- Returning the answer under the wrong key (e.g., `result` instead of `answer`).

## Recommended Patterns
**Pattern 1: Direct answer emission**
1. After you have the result (stored in `$count` or captured from tool output), construct the JSON payload.
2. Call `answer_action` with exactly `{"answer": "<value>"}` where `<value>` is the raw scalar (no extra whitespace, no surrounding text).

CORRECT: `answer_action({"answer": "42"})`
WRONG: `finish_action({"thought": "done"})`
WRONG: `print("The count is 42")`

**Pattern 2: Verification before answering**
- If the result is derived from a pipeline, double‑check the variable is non‑empty.
- If empty, consider whether the correct answer might be `0` and still emit it.

**Pattern 3: Guard against premature termination**
- Do not end the turn with a `finish_action` unless the instruction explicitly asks for a script or file to be created.
- If you are unsure whether the task expects a script, re‑read the instruction; most count/size questions require `answer_action`.

## Example Application
**Task:** "Create a directory `files_list`, write `file_names.txt` with a list of names, then output the number of lines that contain the extension `.txt` as an integer."

**Step‑by‑step:**
1. `mkdir -p files_list`
2. `cat > files_list/file_names.txt <<'EOF'
   a.txt
   b.log
   c.txt
   EOF`
3. `count=$(grep -c "\.txt$" files_list/file_names.txt)`
4. `answer_action({"answer": "$count"})`

**Correct output:** `answer_action({"answer": "2"})`
**Incorrect output:** assistant prints `There are 2 matching lines.` or ends with `finish_action`.

## Success Indicators
- The final turn of the episode is a `answer_action` tool call.
- The payload contains a single key `answer` with the expected scalar value.
- No additional free‑form text is emitted after the `answer_action`.

## Failure Indicators
- The episode ends with `finish_action` or plain text.
- The JSON payload is missing, malformed, or uses the wrong key.
- The answer value is wrapped in extra text (e.g., `"The answer is 5"`).
