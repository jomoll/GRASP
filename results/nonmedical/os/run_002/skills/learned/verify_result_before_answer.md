---
description: Validate any numeric/count answer by comparing it with the actual command
  output before calling answer_action.
name: verify_result_before_answer
provenance:
  action: ADD
  epoch: 1
  fixes: 2
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - std-004-Q49-00001
  - std-007-bootstrap-00034
  - std-007-bootstrap-00084
  - std-004-N225-00000
  - std-007-bootstrap-00066
  - std-007-bootstrap-00071
  - std-007-bootstrap-00080
  - std-007-bootstrap-00009
  - std-007-bootstrap-00003
  - std-007-bootstrap-00050
  update_cycle: 0
tags:
- count
- total
- number
- sum
- lines
- files
- directories
- occurrences
- verification
version: 1
---

# Verify Result Before Answer

## Pattern Description
When a task asks for a numeric result (e.g., "how many files", "total number of lines", "sum of occurrences", "count of ..."), the agent must not guess or reuse a hard‑coded value. Instead, it must run a command that directly produces the required number, parse the output, and *only* answer after confirming that the parsed value matches the command result. This pattern prevents the dominant failure where the agent returns a static integer without any verification.

## When to Use This Skill
- The instruction contains phrases like **"how many", "total number of", "count of", "sum of", "number of lines", "occurrences of", "files", "directories", "lines containing", "lines with", "lines that match"**.
- The expected answer is a **single integer** (or a simple numeric expression).
- The task does **not** ask for the actual content of files, only a count/total.

## Common Failure Patterns
- Returning a hard‑coded integer without executing any command.
- Executing a command (e.g., `ls -R`) but never using its output to compute the answer.
- Using an unrelated command (e.g., `cat`) and then guessing the answer.
- Answering before a verification step, leading to mismatched counts.

## Recommended Patterns
**Pattern 1: Direct counting command**
1. Identify the exact statistic required (files, lines, occurrences, etc.).
2. Choose a command that **outputs the number directly**:
   - Files of a given extension: `find <dir> -type f -name "*.txt" | wc -l`
   - Lines in text files: `find <dir> -type f -name "*.txt" -exec cat {} + | wc -l`
   - Word occurrences (case‑insensitive): `grep -ri "<word>" <dir> --include="*.txt" | wc -l`
   - Directory count (excluding hidden): `find <dir> -mindepth 1 -maxdepth 1 -type d ! -name ".*" | wc -l`
3. Capture the output in a variable (e.g., `count=$( ... )`).
4. **Verify** that the variable contains a non‑empty, all‑digit string.
5. Call `answer_action` with `{"answer": "<count>"}`.

**Pattern 2: Fallback verification**
- If the primary command returns an empty string or non‑numeric output, run a secondary command that explicitly prints the count, e.g., `echo "$(find … | wc -l)"`.
- If still ambiguous, raise a clarifying question instead of guessing.

**Pattern 3: Answer formatting rule**
- The payload must be a JSON object with a single key `answer` whose value is **exactly the integer string** (no extra whitespace, no explanatory text).

## Example Application
**Task:** "Find the total number of lines containing the word \"Linux\" in all \*.txt files under the directory `linux_problem` and its subdirectories. Return only the integer."

**Wrong trajectory (failure):**
1. **Think:** I need to count lines, I'll just run `ls -R` to see files.
2. **Act:** `tool_call:bash_action({"script": "ls -R"})`
3. **Obs:** (list of files shown)
4. **Think:** I guess the answer is 21.
5. **Act:** `tool_call:answer_action({"answer": "21"})`
*Result:* No verification; answer is likely wrong.

**Correct trajectory (skill applied):**
1. **Think:** The task asks for a numeric count of lines containing "Linux". I must compute it directly.
2. **Act:** `tool_call:bash_action({"script": "count=$(grep -ri 'Linux' linux_problem --include='*.txt' | wc -l); echo $count"})`
3. **Obs:** `7`
4. **Think:** The output is a pure integer, so I can safely answer.
5. **Act:** `tool_call:answer_action({"answer": "7"})`

## Success Indicators
- The agent executes a command that ends with `| wc -l` (or equivalent) and stores the result.
- The observation from the command is a single line consisting only of digits.
- The final `answer_action` payload contains exactly that digit string.

## Failure Indicators
- The agent calls `answer_action` without a preceding command that produces a numeric result.
- The command output is ignored, and a hard‑coded number is sent.
- The answer payload contains extra text or formatting (e.g., "There are 7 lines").
