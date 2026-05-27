---
description: "Emit task\u2011specified placeholder when an Observation search returns\
  \ no results"
name: observation_value_extraction_with_placeholder
provenance:
  action: MODIFY
  epoch: 1
  fixes: 12
  parent_version: 1
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - task10_12
  - task10_13
  - task10_8
  - task10_21
  - task10_18
  - task10_24
  - task9_3
  - task2_6
  - task10_15
  update_cycle: 1
tags: []
version: 2
---

# Observation Value Extraction with Placeholder

## Pattern Description
You must extract the most recent numeric value (and its effective date) from a FHIR Observation bundle. If the bundle contains no entries, you must fall back to a placeholder value supplied by the task (or a sensible default such as `-1`). This pattern guarantees that downstream logic (e.g., ordering a repeat lab) always receives a concrete answer instead of an empty result.

## When to Use This Skill
- When a task asks for the "last <lab> value" and you issue a `GET /Observation?code=<code>&patient=<id>` request.
- When the returned Bundle has `total = 0` **or** the `entry` array is missing/empty.
- When the task description includes a placeholder expectation (e.g., "return -1 if no recent result" or "use the task‑specified placeholder").

## Common Failure Patterns
- `total` is `0` but the skill proceeds to read `entry[0]`, causing an index error and returning `[-1]` without explanation.
- The skill ignores a placeholder string embedded in the task context and always returns a hard‑coded value.
- Returning the whole Bundle or an empty array instead of the placeholder.

## Recommended Patterns
**Pattern 1: Primary extraction**
1. Parse the JSON response.
2. If `bundle.total > 0` and `bundle.entry` exists:
   - Locate the entry with the most recent `effectiveDateTime` (or `issued`).
   - Extract `valueQuantity.value` (as a number) and optionally `valueQuantity.unit`.
   - Return `[value]` (or `[value, date]` if the task asks for the date).

**Pattern 2: Placeholder fallback**
1. If `bundle.total == 0` **or** `bundle.entry` is missing/empty:
   - Look for a placeholder in the task context. This is usually provided as a literal in the instruction (e.g., "return -1 if no result").
   - If a placeholder is found, return `[placeholder]`.
   - If no explicit placeholder, default to `[-1]`.

**Pattern 3: Output formatting**
- Always wrap the final numeric answer in a JSON array passed to `FINISH`.
- Do **not** include any explanatory text, units, or dates unless the task explicitly requests them.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6550627? If no result, return -1."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6550627`
2. Response Bundle shows `"total": 0`.
3. Apply Pattern 2: placeholder `-1` is mentioned in the task, so return `FINISH([-1])`.

**Correct output:** `FINISH([-1])`
**Wrong output:** `FINISH([])` or `FINISH(["No result"])`

## Success Indicators
- The agent returns a numeric array (or the placeholder) even when the Observation bundle is empty.
- No index‑out‑of‑range errors occur.
- Downstream skills that depend on the value (e.g., ordering a repeat test) receive the placeholder and act accordingly.

## Failure Indicators
- `FINISH([])` or any non‑numeric payload when the bundle is empty.
- The agent attempts to read `entry[0]` and crashes or returns an error.
- The placeholder value is omitted or replaced with a string.
