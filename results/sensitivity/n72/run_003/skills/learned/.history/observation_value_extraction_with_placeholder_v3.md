---
description: "Extract the most recent numeric observation value and its effectiveDateTime,\
  \ emitting a two\u2011element placeholder (null/null or task\u2011specified) when\
  \ the bundle is empty. Guarantees a two\u2011element array output so downstream\
  \ logic (e.g., age checks) never receives a single\u2011element result like [-1]."
name: observation_value_extraction_with_placeholder
provenance:
  action: MODIFY
  epoch: 3
  fixes: 11
  parent_version: 2
  probe_score: 9
  regressions: 0
  triggering_sample_ids:
  - task10_12
  - task10_21
  update_cycle: 0
tags: []
version: 3
---

## Observation Value Extraction with Timestamp and Safe Placeholder

### Core Extraction Logic
1. **Inspect the Bundle** returned from the Observation search.
2. **Empty‑Bundle Guard**:
   - If `bundle.total == 0` **or** `bundle.entry` is missing, **do not** emit `[-1]`.
   - Determine the placeholder values:
     - If the task context provides explicit placeholders (e.g., `task.placeholderValue` and `task.placeholderTimestamp`), use those.
     - Otherwise default to `null` for both elements.
   - **Return** `FINISH([placeholderValue, placeholderTimestamp])` and **stop** further processing.
3. **Non‑Empty Bundle**:
   - Sort `bundle.entry` by `resource.effectiveDateTime` descending (most recent first).
   - From the first entry (`mostRecent`):
     - **Value**: 
       - Prefer `mostRecent.resource.valueQuantity.value`.
       - If absent, attempt to parse `mostRecent.resource.valueString` as a float.
       - If parsing fails, treat the value as missing and fall back to the placeholder logic from step 2.
     - **Timestamp**: Use `mostRecent.resource.effectiveDateTime`. If missing, fall back to `bundle.meta.lastUpdated`.
   - **Return** `FINISH([value, timestamp])`.

### Fallback / Verification Rules
- If the selected entry lacks a usable numeric value **and** no placeholder was supplied, return `[null, null]`.
- If `effectiveDateTime` is missing, use `bundle.meta.lastUpdated` (ISO‑8601) as the timestamp.

### Formatting Rule
- The final `FINISH` call **must always** contain a JSON array with exactly two elements: a numeric value (or placeholder) and an ISO‑8601 timestamp (or placeholder). No units, notes, or extra fields are included.

### Example
```json
FINISH([6.1, "2023-10-13T22:22:00+00:00"]) // normal case
FINISH([null, null])                         // empty bundle, no task‑specific placeholder
FINISH(["N/A", "2026-05-17T16:46:09+00:00"]) // task supplied custom placeholders
```
