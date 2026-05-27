---
description: Format lab observation answers as a single numeric sentinel, dropping
  timestamps and extra fields
name: structured_lab_observation_answer
provenance:
  action: MODIFY
  epoch: 4
  fixes: 11
  parent_version: 3
  probe_score: 7
  regressions: 0
  triggering_sample_ids:
  - task9_8
  - task2_1
  - task8_23
  - task9_3
  - task9_11
  - task5_7
  - task9_9
  - task9_22
  - task9_20
  - task9_28
  update_cycle: 0
tags: []
version: 4
---

# Structured Lab Observation Numeric Answer

## Pattern Description
You must ensure that any answer derived from a FHIR Observation containing a lab result is returned as a raw numeric sentinel (a one‑element list) rather than a composite list that includes timestamps or other metadata. This keeps downstream logic simple and matches the expected answer format for tasks that ask for "the most recent <lab> value".

## When to Use This Skill
- When a task requests the most recent value of a lab observation (e.g., potassium, magnesium, HbA1c) and you have just performed a `GET /Observation?...` request.
- When the Observation bundle contains entries with `valueQuantity.value` (or a parsable `valueString`).
- When the required answer is a single number or `-1` if no recent measurement exists.

## Common Failure Patterns
- `FINISH([3.8, "2023-11-12T15:12:00+00:00"])` – value and timestamp are both returned.
- Returning the value as a string: `FINISH(["3.8"])`.
- Returning a list of strings that embed the value and units.
- Omitting the sentinel entirely and returning an empty list when a value exists.

## Recommended Patterns
**Pattern 1: Extract numeric value only**
1. After the GET request, locate the first entry in the Bundle (`bundle.entry[0]`).
2. If `entry.resource.valueQuantity` exists, read `valueQuantity.value` (already a number).
3. Else if `entry.resource.valueString` exists, attempt to parse a leading number from the string.
4. If a numeric value is obtained, call `FINISH([value])`.
5. If no entry or no numeric value can be parsed, call `FINISH([-1])`.

**Pattern 2: Fallback when the bundle is empty**
- If `bundle.total == 0` or `bundle.entry` is missing, immediately `FINISH([-1])`.

**Pattern 3: Guard against non‑numeric payloads**
- Verify the extracted value is of type `number`. If it is a string, attempt `parseFloat`; if parsing fails, treat as missing and return `-1`.

## Example Application
**Task:** "Check patient S1635224's most recent potassium level. If low, then order replacement potassium..."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1635224`
2. Receive a Bundle. Assume the first entry contains:
   ```json
   {
     "resource": {
       "valueQuantity": { "value": 3.8, "unit": "mmol/L" },
       "effectiveDateTime": "2023-11-12T15:12:00+00:00"
     }
   }
   ```
3. Extract `valueQuantity.value` → `3.8`.
4. Call `FINISH([3.8])` (no timestamp).
5. Subsequent conditional logic (e.g., `conditional_lab_replacement_order`) can now correctly compare the numeric sentinel.

**Correct output:** `FINISH([3.8])`
**Incorrect output:** `FINISH([3.8, "2023-11-12T15:12:00+00:00"])`

## Success Indicators
- The final `FINISH` call contains exactly one numeric element (or `-1`).
- No timestamp or unit strings appear in the output list.
- Downstream skills that compare the value (e.g., low‑value ordering) receive a number they can evaluate.

## Failure Indicators
- `FINISH` output includes more than one element.
- The element is a string rather than a number.
- The skill does not fire for a valid Observation bundle, leaving the agent to fall back to a default (often a list with value and date).
