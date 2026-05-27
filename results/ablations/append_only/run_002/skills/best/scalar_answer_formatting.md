---
description: Enforce returning plain numeric or string scalars (not quoted numbers)
  in FINISH output
name: scalar_answer_formatting
provenance:
  action: ADD
  epoch: 1
  fixes: 7
  probe_score: 3
  regressions: 4
  triggering_sample_ids:
  - task2_30
  - task8_21
  - task2_22
  - task9_1
  - task4_28
  - task2_26
  - task2_1
  - task2_14
  - task2_6
  - task2_17
  update_cycle: 1
tags: []
version: 1
---

# Scalar Answer Formatting

## Pattern Description
You must ensure that any answer that the task describes as a single numeric or string value is returned as a plain scalar inside the FINISH array.  Numbers must be emitted as JSON numbers (e.g., `80`), not as quoted strings (`"80"`).  Strings (e.g., MRNs) remain quoted.  This rule applies after you have extracted the value from a FHIR resource and before you call `FINISH`.

## When to Use This Skill
- When the instruction says *"answer should be a single number"*, *"rounded down to an integer"*, or similar phrasing.
- When the instruction asks for a single lab value (e.g., magnesium, potassium) and does **not** request the unit to be part of the answer.
- When you have already extracted a value but it is stored as a string (e.g., `"80"`, `"2.1"`).
- When you are about to call `FINISH([...])` and the payload contains an array of quoted numbers.

## Common Failure Patterns
- `FINISH(["80"])` – number returned as a quoted string.
- `FINISH(["2.1 mg/dL"])` – number with unit concatenated into a string when only the numeric value is required.
- `FINISH(["48"])` for age queries – integer quoted.
- Returning a full sentence array (e.g., `FINISH(["Potassium level is 3.8 mmol/L; no replacement needed."])`) when only the numeric value is expected.

## Recommended Patterns
**Pattern 1: Core scalar conversion**
1. After extracting the target field, check its JSON type.
2. If the value is a string that represents a number, convert it:
   ```
   let raw = extractedValue; // e.g., "80"
   let num = Number(raw);
   if (!Number.isNaN(num)) extractedValue = num;
   ```
3. If the task explicitly asks for a unit, keep the unit handling to a separate skill; otherwise strip any unit suffix before conversion.
4. Call `FINISH([extractedValue])`.

**Pattern 2: Fallback when conversion fails**
- If the string cannot be parsed to a number, log a warning and fall back to returning `-1` (or the task‑specified sentinel).

**Pattern 3: Formatting for string answers**
- For identifiers, MRNs, or other pure strings, keep the value quoted and return `FINISH(["value"])`.

## Example Application
**Task:** "What's the age of the patient with MRN of S2703270?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2703270`
2. Extract `birthDate` from the returned Patient resource.
3. Compute age (e.g., `2023-11-13` – `birthDate`).
4. The computed age is a number (`80`). Ensure it is a JSON number, not a string.
5. `FINISH([80])`

**Correct output:** `FINISH([80])`
**Wrong output:** `FINISH(["80"])`

## Success Indicators
- The `FINISH` payload contains an array with a JSON number for numeric answers.
- No surrounding quotes around numeric values.
- Unit‑less answers when the task does not request the unit.

## Failure Indicators
- `FINISH` contains quoted numbers.
- The answer includes extra text or units that were not asked for.
- The agent returns an empty array when a valid scalar exists.

---

*Tags:* ["formatting", "scalar", "numeric", "answer"]
