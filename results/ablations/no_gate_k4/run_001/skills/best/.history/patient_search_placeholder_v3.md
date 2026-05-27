---
description: Return a structured placeholder for missing patient instead of a plain
  string
name: patient_search_placeholder
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task1_27
  - task8_14
  - task10_20
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task5_16
  - task9_11
  update_cycle: 0
tags: []
version: 3
---

# Patient Search Placeholder

## Pattern Description
You must handle the case where a FHIR Patient search returns an empty Bundle. Instead of echoing a free‑text string like "Patient not found", emit a deterministic JSON placeholder that downstream logic can recognise. This makes the agent’s answer format consistent across all "not‑found" scenarios and prevents the "patient_not_found_assumption" regression.

## When to Use This Skill
- When a `GET /Patient` request returns a Bundle with `total: 0`.
- When the task explicitly asks for the MRN or a message if the patient does not exist.
- Any time the agent is about to call `FINISH` with a plain string indicating a missing patient.

## Common Failure Patterns
- `FINISH(["Patient not found"])` – plain string output.
- Returning `null` or an empty array without context.
- Mixing the placeholder with other unrelated data in the same FINISH call.

## Recommended Patterns
**Pattern 1: Core placeholder strategy**
1. Detect that the Bundle `total` field is `0`.
2. Construct a JSON object with the exact fields:
   ```json
   {
     "mrn": null,
     "message": "Patient not found"
   }
   ```
3. Call `FINISH` with that object as the sole element of the result array.
   - **CORRECT**: `FINISH([{"mrn":null,"message":"Patient not found"}])`
   - **WRONG**: `FINISH(["Patient not found"])`

**Pattern 2: Fallback when the API response is malformed**
- If the response is not a valid Bundle, still emit the same placeholder rather than raising an error.

**Pattern 3: Formatting rule**
- Do **not** wrap the placeholder in an extra array layer; the outer FINISH array is required, but the placeholder itself must be a single JSON object.

## Example Application
**Task:** "What’s the MRN of the patient with name Tina Reid and DOB of 1953-10-18? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?name=Tina%20Reid&birthdate=1953-10-18`
2. Inspect the returned Bundle – `"total": 0`.
3. Build the placeholder object `{ "mrn": null, "message": "Patient not found" }`.
4. `FINISH([{"mrn":null,"message":"Patient not found"}])`

**CORRECT output:** `FINISH([{"mrn":null,"message":"Patient not found"}])`
**WRONG output:** `FINISH(["Patient not found"])`

## Success Indicators
- The agent’s final `FINISH` payload contains a single JSON object with the keys `mrn` and `message`.
- No plain strings appear in the output for missing‑patient cases.
- Downstream tests that parse the placeholder succeed without type errors.

## Failure Indicators
- The output is a plain string or an empty array.
- The placeholder object is missing either the `mrn` or `message` field.
- Additional unrelated data is mixed into the placeholder.
