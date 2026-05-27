---
description: Validate and compute the exact metric(s) requested (lines, words, characters,
  bytes, files, directories, etc.) before answering, **but only when the task expects
  a numeric answer rather than a script or command**.
name: metric_computation_check
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - std-004-Q49-00001
  - std-007-bootstrap-00006
  - std-007-bootstrap-00034
  - std-001-stock-00002
  - std-007-bootstrap-00007
  - std-004-N37-00000
  - std-005-new-00003
  - std-007-bootstrap-00051
  - std-007-bootstrap-00057
  - std-007-bootstrap-00003
  update_cycle: 0
tags:
- metric_computation_check
version: 1
---

## Metric Computation Check (Narrowed Trigger)

### Guard Clause
Before applying this skill, scan the instruction for any of the following cue words/phrases that indicate the user wants a **script, command, or code snippet** instead of a raw numeric answer:
- "script"
- "bash script"
- "write a script"
- "provide a command"
- "show how to"
- "demonstrate"
- "example"
- "code"
If any of these appear, **skip this skill** and let the normal reasoning proceed.

### When to Use (after guard passes)
- The instruction contains any of the keywords **lines**, **words**, **characters**, **bytes**, **size**, **files**, **directories**, **folders**, **total**, **sum**, or a combination thereof.
- The wording explicitly asks for *the total number of* X, *the sum of* X, or to *return the count/size* directly.

### Pattern 1: Identify Required Metrics
1. Parse the task text and build a list `metrics` containing any of: `lines`, `words`, `chars`, `bytes`, `files`, `dirs`.
2. For each metric decide the exact command (using the directory/path supplied in the instruction):
   - `lines` → `find <dir> -type f -print0 | xargs -0 cat | wc -l`
   - `words` → same pipeline with `wc -w`
   - `chars` / `bytes` → same pipeline with `wc -c`
   - `files` → `find <dir> -type f | wc -l`
   - `dirs` → `find <dir> -type d | wc -l`
3. Execute **each command separately** and capture the integer output.

### Pattern 2: Verify Output Shape
- After each command, ensure the observation matches `^[0-9]+$`. If not, retry with a safer variant (e.g., add `-maxdepth 0` for top‑level only).
- If the task asks for a *sum* of several metrics, compute the arithmetic sum locally after all values are collected.

### Pattern 3: Answer Formatting
- Call `answer_action` **once**, with a JSON payload containing a single integer `answer` that matches the exact value requested.
- Do **not** include any extra text, units, or newline characters.

### Success Indicators
- Separate commands are run for each requested metric.
- Each command’s observation is a solitary integer.
- The final `answer_action` payload contains exactly the integer (or correct sum) the task asked for.

### Failure Indicators
- A single `wc` call is used when multiple metrics are requested.
- The agent returns raw multi‑field `wc` output or includes units/text.
- The answer does not match the required metric or sum.
- The agent calls `finish_action` instead of `answer_action`.
