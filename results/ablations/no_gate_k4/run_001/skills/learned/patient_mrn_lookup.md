---
description: "Extract a patient\u2019s MRN from a Patient resource and output it as\
  \ a plain string"
name: patient_mrn_lookup
provenance:
  action: ADD
  epoch: 2
  no_gate: true
  triggering_sample_ids:
  - task1_12
  - task1_20
  - task1_11
  - task1_16
  - task1_13
  - task10_10
  - task10_12
  - task10_13
  - task9_1
  - task1_26
  update_cycle: 1
tags:
- patient
- identifier
- mrn
version: 1
---

# Patient MRN Lookup

## Pattern Description
When a task asks for the Medical Record Number (MRN) of a patient identified by name and date of birth, you must search for the matching `Patient` resource, extract the identifier that represents the MRN, and return it as a plain string.  If no matching patient exists, return the structured placeholder defined by `patient_search_placeholder` instead of a raw string.

## When to Use This Skill
- The instruction explicitly requests the MRN (e.g., "What’s the MRN of the patient with name X and DOB Y?").
- The task may also include a conditional clause for non‑existent patients.
- The agent has already performed a `GET /Patient?name=...&birthdate=...` (or similar) and received a Bundle.

## Common Failure Patterns
- Returning the entire Patient JSON or a list instead of just the MRN string.
- Forgetting to handle the case where `Bundle.total == 0`, leading to an empty answer or wrong type.
- Outputting the MRN inside an array (e.g., `FINISH(["S123456"])`) when the task expects a plain string.

## Recommended Patterns
**Pattern 1: Core extraction rule**
1. Issue `GET {base}/Patient?name={fullName}&birthdate={dob}`.
2. If `Bundle.total == 0`, invoke `patient_search_placeholder` and return its result.
3. Otherwise, locate the first `entry.resource` of type `Patient`.
4. Within `resource.identifier`, find the identifier whose `type.coding.code` or `type.text` indicates "MRN" (or assume the first identifier if only one exists).
5. Extract `identifier.value` as a string.
6. Return `FINISH(mrnString)` **without** surrounding brackets.

**Pattern 2: Missing‑patient fallback**
- Call the existing `patient_search_placeholder` skill to produce a structured placeholder such as `{ "mrn": null, "note": "Patient not found" }`.
- Return that placeholder directly.

## Example Application
**Task:** "What’s the MRN of the patient with name Margaret Kidd and DOB of 1982-08-24? If the patient does not exist, the answer should be a placeholder."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?name=Margaret%20Kidd&birthdate=1982-08-24`
2. Bundle `total = 1`; entry contains `identifier[0].value = "S987654"`.
3. Extract `"S987654"`.
4. `FINISH("S987654")`.

If the Bundle had `total = 0`, the skill would call `patient_search_placeholder` and return its structured result.

## Success Indicators
- The final output is a plain string MRN (e.g., `FINISH("S987654")`).
- When no patient is found, the output matches the placeholder format defined by `patient_search_placeholder`.
- No extra JSON structures or arrays are present unless explicitly required by the placeholder.

## Failure Indicators
- The answer is an array or object when a plain string is required.
- The MRN is omitted or the placeholder is not used for missing patients.
- The agent returns the full Patient resource instead of just the identifier.
