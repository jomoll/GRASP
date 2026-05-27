---
description: "Add precise triggers and commands for non\u2011empty line counts and\
  \ size aggregation by file extension."
name: file_metric_aggregation
provenance:
  action: MODIFY
  epoch: 2
  fixes: 3
  parent_version: 1
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - std-004-Q49-00001
  - std-007-bootstrap-00006
  - std-007-bootstrap-00034
  - std-001-stock-00002
  - std-007-bootstrap-00011
  - std-007-bootstrap-00007
  - std-004-N37-00000
  - std-005-new-00003
  - std-001-stock-00004
  - std-007-bootstrap-00051
  update_cycle: 0
tags:
- lines
- non-empty
- size
- bytes
- extension
- count
- aggregation
version: 2
---

# File Metric Aggregation (Enhanced)

## Pattern Description
You need to compute a numeric metric that summarizes properties of a set of files. The metric can be a **line‑based count** (total lines, non‑empty lines) or a **size‑based sum** (total bytes of files matching a given extension). The skill chooses the correct command based on the wording of the task and then formats the answer as a plain integer via `answer_action`.

## When to Use This Skill
- The instruction asks for *"number of lines"*, *"non‑empty lines"*, *"total lines"*, or any phrasing that distinguishes empty from non‑empty lines.
- The instruction asks for the *"total size"*, *"sum of sizes"*, *"bytes"* of files with a particular *extension* (e.g., ".txt", ".log").
- The task mentions *"count"* together with a file type or extension but does **not** say *"count files"* (i.e., the metric is about the contents of the files, not the file count).

## Common Failure Patterns
- Using `find … | wc -l` which counts files instead of lines.
- Using `wc -l` on a set of files without filtering empty lines, leading to inclusion of blank lines.
- Summing file counts with `du -sh` or similar, producing a human‑readable size string instead of a raw byte total.
- Forgetting to restrict the search to the requested extension, causing unrelated files to be included.

## Recommended Patterns
**Pattern 1: Non‑empty line count across one or many files**
1. Identify the target file(s) from the task (single file path or a directory + extension).
2. If a directory and extension are given, use:
   ```bash
   grep -v '^$' -h "${DIR}"/*.${EXT} | wc -l
   ```
   - `-h` suppresses filenames in output.
   - `grep -v '^$'` removes empty lines.
3. If only a single file is given, use:
   ```bash
   grep -v '^$' "${FILE}" | wc -l
   ```
4. Capture the numeric output and call:
   ```json
   {"answer": "<count>"}
   ```

**Pattern 2: Total byte size of files with a specific extension**
1. Locate all regular files matching the extension:
   ```bash
   find "${DIR}" -type f -name "*.${EXT}" -exec stat -c%s {} +
   ```
2. Sum the sizes:
   ```bash
   ... | awk '{sum+=$1} END {print sum}'
   ```
   (You can pipe the `find` output directly into `awk`.)
3. Return the sum as an integer via `answer_action`.

**Pattern 3: Fallback verification**
- After computing the metric, optionally double‑check with an alternative command:
  - For line counts: `awk 'NF' "${FILE}" | wc -l` should match the `grep` result.
  - For size sums: `du -b "${DIR}"/*.${EXT} 2>/dev/null | awk '{sum+=$1} END {print sum}'`.
- If the two results differ, re‑run with a more explicit command (e.g., use `stat` per file).

## Example Application
**Task:** "Count the number of non‑empty lines in `system_logs.txt`."

**Step‑by‑step:**
1. *Think:* The task asks for non‑empty lines → use Pattern 1.
2. *Act:*
   ```json
   {"tool":"bash_action","script":"grep -v '^$' system_logs.txt | wc -l"}
   ```
3. *Observation:* `13`
4. *Think:* The output is a single integer, ready to answer.
5. *Act:*
   ```json
   {"tool":"answer_action","answer":{"answer":"13"}}
   ```

**Wrong trajectory (failure):**
1. *Think:* Need a count → mistakenly use file count.
2. *Act:* `find . -mindepth 1 | wc -l`
3. *Observation:* `13` (actually file count, not line count).
4. *Think:* Assume correct and answer `13`.
5. *Act:* `answer_action` with `13` → metric is wrong.

## Success Indicators
- The agent selects `grep -v '^$' … | wc -l` (or the `awk` equivalent) for non‑empty line tasks.
- The agent uses `find … -name "*.ext" -exec stat -c%s {} + | awk …` for size‑by‑extension tasks.
- The final `answer_action` payload contains only the integer metric, no extra text.

## Failure Indicators
- The agent runs `find … | wc -l` when the task mentions lines.
- The agent returns a human‑readable size like `492M` instead of a raw byte count.
- The answer payload includes explanatory text or the raw command output.
