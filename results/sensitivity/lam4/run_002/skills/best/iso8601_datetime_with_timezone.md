---
description: "Enforce ISO\u20118601 timestamps with explicit timezone offset in all\
  \ FINISH outputs."
name: iso8601_datetime_with_timezone
provenance:
  action: ADD
  epoch: 1
  fixes: 12
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_20
  - task10_10
  - task1_7
  - task10_16
  - task4_28
  - task10_8
  - task10_24
  - task9_9
  update_cycle: 0
tags: []
version: 1
---

# ISO8601 DateTime with Timezone Enforcement

## Pattern Description
You must always return date‑time values in full ISO‑8601 format **including** a timezone offset (e.g. `2023-11-09T10:06:00+00:00`).  Many FHIR resources store timestamps without an explicit offset, but downstream logic and the evaluation harness expect a complete timestamp.  This skill normalises any extracted datetime string before it is placed in the FINISH array.

## When to Use This Skill
- When a task asks for "when was it recorded" or any other timestamp derived from `effectiveDateTime`, `issued`, `authoredOn`, etc.
- When the agent is about to `FINISH` an array that contains a datetime string.
- When the source value lacks a timezone designator (e.g. `2023-10-13` or `2023-10-13T10:06:00`).

## Common Failure Patterns
- Returning `"2023-10-13"` – date only, no time or offset.
- Returning `"2023-10-13T10:06:00"` – time present but missing `+00:00` (or other offset).
- Mixing formats: sometimes a full timestamp, sometimes a plain date, causing inconsistent downstream checks.

## Recommended Patterns
**Pattern 1: Normalise extracted datetime**
1. Identify the field that holds the datetime (e.g. `effectiveDateTime`).
2. Parse the string with a robust ISO‑8601 parser.
3. If the parsed value has no offset, **assume UTC** (or the context `Current time` timezone) and append `+00:00`.
4. If the parsed value has only a date, append `T00:00:00+00:00`.
5. Convert the result back to a string in the exact form `YYYY-MM-DDTHH:MM:SS+ZZ:ZZ`.

**CORRECT**: `"2023-10-13T10:06:00+00:00``
**WRONG**: `"2023-10-13``, `"2023-10-13T10:06:00``

**Pattern 2: Fallback handling**
- If parsing fails entirely, fall back to the task’s provided "Current time" value (which already includes a timezone) and use that as the timestamp.

**Pattern 3: FINISH formatting**
- When constructing the FINISH array, place the normalised datetime string as a plain JSON string element, not inside an object or with extra whitespace.

## Example Application
**Task:** "What’s the last HbA1C value in the chart for patient S3114648 and when was it recorded?"

**Step‑by‑step:**
1. `GET /Observation?code=A1C&patient=S3114648`.
2. Extract `effectiveDateTime` from the most recent entry, e.g. `"2023-10-13"`.
3. Detect missing time/offset → append `T00:00:00+00:00` → `"2023-10-13T00:00:00+00:00"`.
4. Extract the numeric value `6.1`.
5. `FINISH([6.1, "2023-10-13T00:00:00+00:00"])`.

**CORRECT output:** `FINISH([6.1, "2023-10-13T00:00:00+00:00"])`
**WRONG output:** `FINISH([6.1, "2023-10-13"])`

## Success Indicators
- Every FINISH array that includes a datetime string ends with `+hh:mm` (e.g. `+00:00`).
- The evaluation log shows no `datetime_missing_timezone` failures.
- Unit tests that compare timestamps succeed without format errors.

## Failure Indicators
- FINISH output contains a date without `T` or without `+hh:mm`.
- The agent logs a warning about “missing timezone”.
- The same task repeats the failure after the skill is added.
