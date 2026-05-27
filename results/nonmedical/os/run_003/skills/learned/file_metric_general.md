---
description: "Handle generic file\u2011system metric requests (line count, file/count\
  \ size, existence, path lookup, process count)."
name: file_metric_general
provenance:
  action: ADD
  epoch: 1
  fixes: 1
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - std-007-bootstrap-00084
  - std-005-new-00000
  - std-007-bootstrap-00030
  - std-004-Q49-00000
  - std-007-bootstrap-00034
  - std-007-bootstrap-00019
  - std-007-bootstrap-00050
  - std-004-Q19-00000
  - std-007-bootstrap-00038
  - std-004-N37-00000
  update_cycle: 1
tags: []
version: 1
---

# File Metric General

## Pattern Description
You must recognize any task that asks for a quantitative metric about files, directories, or processes – e.g. line counts, file counts, total size, existence checks, full paths, or the number of running processes. Instead of doing nothing, choose a small, direct Bash command that returns the exact scalar value required and feed it to `answer_action`. The skill isolates the intent, selects the appropriate command, and formats the answer as a plain string (no extra text).

## When to Use This Skill
- Instruction contains **"how many"**, **"number of"**, **"total"**, **"count"**, **"size"**, **"storage"**, **"bytes"**, **"kilobytes"**, **"lines"**, **"empty files"**, **"empty directories"**, **"exists"**, **"full path"**, **"path of"**, **"where is"**, **"processes"**, or **"active processes"**.
- The request refers to a **file**, **directory**, **extension**, or **process** and expects a single integer or size string as answer.

## Common Failure Patterns
- Agent performs no action (START_FAILED) because it does not recognize the request as a metric query.
- Using a generic `ls` or `cat` and then manually counting from truncated output.
- Returning a raw script or description instead of calling `answer_action` with the computed value.
- Mixing units (e.g., returning `5M` when the task asked for an integer kilobyte count).

## Recommended Patterns
**Pattern 1: Identify the metric type**
1. Scan the instruction for keywords.
2. Map to one of the concrete commands below.

**Pattern 2: Core commands**
| Metric | Bash command (replace `<path>` and `<ext>` as needed) |
|--------|-------------------------------------------------------|
| Line count in a file | `wc -l <path> | awk '{print $1}'` |
| File count (any) | `find <path> -type f | wc -l` |
| File count with extension | `find <path> -type f -name "*.<ext>" | wc -l` |
| Total size (bytes) | `find <path> -type f -exec stat -c%s {} + | awk '{sum+=$1} END {print sum}'` |
| Total size (KB) | `du -sk <path> | cut -f1` |
| Empty files count | `find <path> -type f -empty | wc -l` |
| Empty directories count | `find <path> -type d -empty | wc -l` |
| Existence of a regular file | `if [ -f "<path>" ]; then echo yes; else echo no; fi` |
| Full path of a named executable/file | `command -v <name> || find / -type f -name <name> 2>/dev/null | head -n1` |
| Total number of active processes | `ps -e --no-headers | wc -l` |

**Pattern 3: Answer formatting**
- Capture only the numeric or path string from the command output.
- Call `answer_action({"answer": "<value>"})` immediately.
- Do **not** emit any explanatory text.

## Example Application
**Task:** "How many lines are there in /root/matrix.txt?"

**Wrong trajectory (failure)**
1. *Think*: The instruction looks like a question, but I have no matching skill.
2. *Act*: (none) → START_FAILED.
3. *Observation*: error `START_FAILED`.

**Correct trajectory (skill applied)**
1. *Think*: The phrase "how many lines" signals a line‑count metric.
2. *Act*: `bash_action({"script": "wc -l /root/matrix.txt | awk '{print $1}'"})`
3. *Observation*: OS returns `42`.
4. *Think*: The output is the exact answer.
5. *Act*: `answer_action({"answer": "42"})`

## Success Indicators
- The agent selects a concrete Bash command matching the metric type.
- The command runs without error and returns a single scalar value.
- The final action is `answer_action` with a JSON payload containing only that value.

## Failure Indicators
- The agent emits no `bash_action` (START_FAILED) or returns a script description.
- The answer includes extra wording or units not requested.
- The chosen command does not directly produce the scalar (e.g., using `ls` then manual count).
