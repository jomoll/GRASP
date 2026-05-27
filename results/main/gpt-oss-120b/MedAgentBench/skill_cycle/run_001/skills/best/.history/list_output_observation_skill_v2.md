---
description: "Enforce list\u2011format and ISO\u20118601 datetime for Observation\
  \ value\u2011date answers, but only when the task is actually about an Observation\
  \ (i.e., the request targets the Observation endpoint or the task text mentions\
  \ a lab/value/date). This guard prevents the skill from interfering with unrelated\
  \ queries such as patient\u2011lookup tasks."
name: list_output_observation_skill
provenance:
  action: MODIFY
  epoch: 0
  fixes: 13
  parent_version: 1
  probe_score: 5
  regressions: 2
  triggering_sample_ids:
  - task5_19
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task1_16
  - task5_16
  - task9_28
  - task9_8
  update_cycle: 1
tags: []
version: 2
---

## Observation List Output with ISO‑8601 Date Check (guarded)

### Trigger Guard
- **Activate this skill only if** one of the following is true:
  1. The most recent API call in the current trace is a `GET` (or `POST`/`PUT`) to a URL that contains `/Observation` (case‑insensitive).
  2. The task description (or any preceding system instruction) contains any of the keywords: `lab`, `value`, `result`, `date`, `recorded`, `Observation`, `test`, `HbA1c`, `cholesterol`, `creatinine`, etc.
- If neither condition is met, the agent should **skip** this skill and proceed with the default behavior.

### Pattern Description (unchanged when guard passes)
You must return Observation results as a JSON list where each element is a two‑item array: the numeric value and the **full ISO‑8601 datetime** of the observation. This pattern applies to any task that asks for the most recent lab value together with its recorded date (e.g., HbA1c, cholesterol, creatinine). By enforcing the datetime format you avoid downstream parsing errors and enable correct age‑based logic such as “order a new test if the result is older than one year”.

### When to Use This Skill (after guard passes)
- When a task requests *"the last <lab> value and when it was recorded"*.
- When the answer must be used in a conditional check on the result date (e.g., > 1 year old).
- When the expected output format is a list `[value, "YYYY‑MM‑DDThh:mm:ss+zz:zz"]`.

### Common Failure Patterns
- Returning only a date string like `"2023-10-13"` (missing time and timezone).
- Using a human‑readable format such as `"Oct 13, 2023"`.
- Omitting the datetime field entirely and returning just the value.
- Mixing types: returning the date as a number or embedding it in a sentence.

### Recommended Patterns (executed only when guard passes)
**Pattern 1: Core extraction and formatting**
1. From the Observation bundle, locate the entry with the highest `effectiveDateTime` (or `issued` if `effectiveDateTime` missing).
2. Extract `valueQuantity.value` (or the appropriate numeric field) as a **number**.
3. Extract `effectiveDateTime` as a string. If the field is missing, fall back to `issued`.
4. Ensure the datetime string matches the regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$`. If it does not, **append** `"T00:00:00+00:00"` to the date.
5. Return `FINISH([value, "datetime"])`.

**Pattern 2: Fallback when no Observation found**
- If the search returns zero entries, return `FINISH([-1])` (or the task‑specific sentinel) **without** attempting a date.

**Pattern 3: Using the date in downstream logic**
- After extracting the datetime, compare it to the current context time (provided in the task description) using ISO‑8601 comparison. If the difference > 1 year, trigger the ordering step defined by the task.

### Example Application (guard passes because request is to Observation)
**Task:** "What’s the last HbA1C value for patient S3114648 and when was it recorded? If the result date is > 1 year old, order a new HbA1C lab test."
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S3114648`
2. Pick the Observation with the greatest `effectiveDateTime`.
3. Extract `valueQuantity.value` → `6.1`.
4. Extract `effectiveDateTime` → `2023-10-13T09:45:00+00:00`.
5. Compare to current time `2023-11-13T10:15:00+00:00`; difference is 31 days → **no** new order.
6. `FINISH([6.1, "2023-10-13T09:45:00+00:00"])`.

### Success Indicators
- The FINISH payload is a two‑item list where the second item matches the ISO‑8601 pattern **and** the guard conditions were satisfied.
- Any conditional ordering logic runs only when the datetime comparison indicates the result is older than the required threshold.

### Failure Indicators
- The second element of the list is a plain date (`YYYY‑MM‑DD`) or a human‑readable string.
- The agent returns a sentence instead of a list.
- The ordering step is triggered without a proper date comparison.
- The skill fires on a non‑Observation task (e.g., patient MRN lookup) – this is now prevented by the guard.

**Tags:** ["observation", "date_format", "list_output", "conditional_order"]
