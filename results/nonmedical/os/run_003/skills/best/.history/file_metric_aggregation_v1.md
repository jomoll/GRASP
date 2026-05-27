---
description: "Select and compute the correct line\u2011count or byte\u2011size metric\
  \ for files matching a given extension."
name: file_metric_aggregation
provenance:
  action: ADD
  epoch: 0
  fixes: 0
  probe_score: 1
  regressions: 0
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
- lines
- size
- bytes
- count
- code
- extension
- aggregation
version: 1
---

# File Metric Aggregation

## Pattern Description
This skill ensures the agent picks the right aggregation metric when a task asks for *total lines of code*, *total number of lines*, or *total size in bytes* of a set of files. Instead of using generic commands like `du` (which reports directory size) or counting files, the agent must locate the target files, then either sum their line counts (optionally ignoring blank lines) or sum their byte sizes. The pattern is reusable for any file extension and any directory supplied at runtime.

## When to Use This Skill
- The instruction contains phrases like **"total lines of code"**, **"total number of lines"**, **"count lines"**, **"ignore empty lines"**, **"total size of files"**, **"sum of file sizes"**, or **"total bytes"**.
- The task also specifies a *file extension* (e.g., `.py`, `.c`, `.txt`) and a *directory path*.
- The expected answer is a single integer representing either the line count or the byte total.

## Common Failure Patterns
- Using `du -sb` or `du -sh` and returning the directory size instead of summing file sizes.
- Running `find … | wc -l` and returning the *file count* when the task asks for total lines or total bytes.
- Counting all lines with `wc -l` on concatenated files but **including empty lines** when they should be ignored.
- Forgetting to filter by the required extension, thus aggregating unrelated files.

## Recommended Patterns
**Pattern 1: Total non‑empty line count**
1. Locate files: `find "$DIR" -type f -name "*$EXT"`
2. Concatenate and count non‑empty lines: `find "$DIR" -type f -name "*$EXT" -exec cat {} + | grep -c '.'`
3. Store result in `lines` and call `answer_action({"answer": "$lines"})`.

**Pattern 2: Total byte size**
1. Locate files: `find "$DIR" -type f -name "*$EXT"`
2. Sum sizes: `find "$DIR" -type f -name "*$EXT" -exec stat -c%s {} + | awk '{sum+=$1} END {print sum}'`
3. Store result in `bytes` and call `answer_action({"answer": "$bytes"})`.

**Pattern 3: Verification fallback**
- After computing the metric, optionally re‑run a sanity check (e.g., `echo "$lines" | grep -E '^[0-9]+$'`) and retry with a different command (`grep -c '^.'` vs `awk 'NF'`) if the result is empty or non‑numeric.

**Pattern 4: Answer formatting**
- The final payload must be a plain integer inside the JSON `answer` field; no extra text, units, or explanations.

## Example Application
**Task:** "Count the total number of lines of code in all Python (`.py`) files under the directory `$PROJECT_DIR`, ignoring empty lines. Return the count as an integer."

**Wrong trajectory (failure):**
1. *Think:* I need the total size, so I’ll use `du`.
2. *Act:* `tool_call:bash_action({"script": "du -sb $PROJECT_DIR | cut -f1"})`
3. *Obs:* `123456`
4. *Think:* That looks like a number, I’ll answer it.
5. *Act:* `tool_call:answer_action({"answer": "123456"})`
   *Result:* Wrong metric – directory size, not line count.

**Correct trajectory (skill applied):**
1. *Think:* The task asks for total *lines of code* in `.py` files, ignoring blanks.
2. *Act:* `tool_call:bash_action({"script": "find \"$PROJECT_DIR\" -type f -name '*.py' -exec cat {} + | grep -c '.'"})`
3. *Obs:* `842`
4. *Think:* The observation is a plain integer, ready for answer.
5. *Act:* `tool_call:answer_action({"answer": "842"})`
   *Result:* Correct metric – summed non‑empty lines.

## Success Indicators
- The agent runs a `find … -name "*$EXT"` command before any aggregation.
- The output observed is a single integer with no extra characters.
- The final `answer_action` payload contains only that integer.

## Failure Indicators
- The agent calls `du` or `wc -l` on a directory listing instead of on the file contents.
- The answer includes units (`KB`, `bytes`) or explanatory text.
- The computed number is suspiciously small (e.g., equal to the number of files) for a line‑count task.
