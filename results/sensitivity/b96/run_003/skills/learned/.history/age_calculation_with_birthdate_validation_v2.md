---
description: "Compute patient age only when the task explicitly asks for the patient\u2019\
  s age. The skill now first checks the task description for age\u2011related keywords\
  \ (e.g., \"age\", \"how old\", \"years old\"). If the request is not an age query,\
  \ the skill does nothing, allowing other skills to handle the task. When triggered,\
  \ it validates the `birthDate`, computes the floor of the year difference using\
  \ the provided context time, and returns a **bare integer** via `FINISH(age)`. No\
  \ JSON array, string, or other wrapper is used."
name: age_calculation_with_birthdate_validation
provenance:
  action: MODIFY
  epoch: 1
  fixes: 8
  parent_version: 1
  probe_score: 7
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task10_17
  - task8_29
  - task2_17
  - task4_28
  - task9_28
  - task4_15
  - task9_22
  - task4_23
  - task2_25
  update_cycle: 0
tags: []
version: 2
---

## Age Calculation with Birthdate Validation – Guarded Version

### Trigger Guard
1. **Inspect the task description** (`task.description`).
2. Proceed only if the description matches one of the following (case‑insensitive) patterns:
   - `\bage\b`
   - `\bhow old\b`
   - `\byears? old\b`
   - `\bpatient age\b`
3. If none of the patterns are found, **exit the skill** (no action, no FINISH). This prevents the skill from interfering with non‑age tasks such as MRN lookup, observation recording, or service request creation.

### Age Calculation (executed only when the guard passes)
1. **Validate `birthDate`**
   - Locate the first `Patient` entry in the returned `Bundle`.
   - Ensure `birthDate` exists and matches ISO‑8601 (`YYYY-MM-DD` or full datetime).
   - If missing/invalid → `FINISH("Patient birthDate unavailable")`.
2. **Parse dates**
   - Convert `birthDate` to a date object.
   - Use the context time supplied in `task.context` (e.g., `2023-11-13T10:15:00+00:00`). If not provided, fall back to the system’s current UTC time.
3. **Compute age**
   - `age = context_year - birth_year`
   - If the month/day of the context date is before the month/day of the birth date, subtract 1 (floor the year difference).
4. **Return result**
   - `FINISH(age)` where `age` is a numeric literal (e.g., `FINISH(76)`).

### Failure Cases
- If the guard does not match, the skill performs **no action**, allowing other skills to run.
- If `birthDate` is absent or malformed, return the explicit message as above.
- Always emit a plain integer for successful age calculations; never wrap it in an array or string.

### Example
**Task:** "What’s the age of the patient with MRN S2874099?"
- Guard matches → proceed.
- GET Patient → `birthDate = 1947-05-12`.
- Context time = `2023-11-13T10:15:00+00:00`.
- Compute age = 76.
- Output: `FINISH(76)`.

**Non‑age task (e.g., MRN lookup):**
- Guard does not match → skill exits, agent continues with its normal flow, producing `FINISH("Patient not found")` (or other appropriate response) without interference.

---
*No changes to other skills; this modification only narrows the activation condition of the age‑calculation skill.*
