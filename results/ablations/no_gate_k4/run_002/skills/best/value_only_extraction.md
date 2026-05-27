---
description: Ensure lab values are returned as a single scalar string, not a nested
  array
name: value_only_extraction
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task10_24
  - task4_27
  - task9_5
  - task10_21
  - task9_11
  - task10_20
  - task4_4
  - task10_13
  update_cycle: 0
tags:
- extraction
- formatting
version: 2
---

# Value Only Extraction

## Pattern Description
You must extract the numeric lab result and its unit from an Observation and return it as a **single scalar string**. The outer FINISH payload is always an array of arguments, but each argument must be a plain scalar (string or number). Do not wrap the extracted value in an additional array.

## When to Use This Skill
- When a task asks for "the most recent *X* level" or "the last *Y* value" and expects a single value.
- After a GET request to `/Observation` that returns a Bundle with at least one entry.
- When the Observation uses `valueQuantity` (or `valueString` for free‑text results).

## Common Failure Patterns
- Returning `FINISH([ ["1.8 mg/dL"] ])` – a nested array instead of a scalar.
- Concatenating the unit with extra brackets, e.g. `"[1.8] mg/dL"`.
- Omitting the unit entirely, yielding just `"1.8"`.

## Recommended Patterns
**Pattern 1: Core extraction**
1. Verify the GET response is a Bundle with `total > 0`.
2. Locate the first entry: `entry[0].resource`.
3. If `valueQuantity` exists, read:
   - `value = valueQuantity.value`
   - `unit = valueQuantity.unit`
4. If `valueString` exists (e.g., free‑text), use that directly as the scalar.
5. Combine as `scalar = f"{value} {unit}"` (note the space).
6. Call `FINISH([scalar])`.

**Pattern 2: Missing observation fallback**
- If `total == 0`, return the placeholder defined by the task (e.g., `-1` or "no result").
- Call `FINISH([placeholder])`.

**Pattern 3: Type safety check**
- Ensure `scalar` is a string (or number) before FINISH. If it is a list, flatten it.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S6227720 within last 24 hours?"

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S6227720&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00&_sort=-date&_count=1`
2. Response Bundle has `entry[0].resource.valueQuantity.value = 1.8` and `unit = "mg/dL"`.
3. Build `scalar = "1.8 mg/dL"`.
4. `FINISH(["1.8 mg/dL"])`.

**Correct output:** `FINISH(["1.8 mg/dL"])`
**Incorrect output:** `FINISH([["1.8 mg/dL"]])`

## Success Indicators
- The FINISH payload contains exactly one argument that is a plain string like `"1.8 mg/dL"`.
- No extra brackets or nested arrays are present.
- The unit matches the expected unit for the lab code.

## Failure Indicators
- FINISH shows a nested array (`[[...]]`).
- The output string is missing a space before the unit (`"1.8mg/dL"`).
- The agent returns an empty FINISH or a placeholder when a valid observation exists.
