---
description: "Compute patient age correctly, handling birthdays that have not yet\
  \ occurred this year. **Trigger only when the task explicitly asks for the patient's\
  \ age** (e.g., contains the word \"age\", \"years old\", \"how old\", or similar).\
  \ If the task does not contain such a keyword, the skill must not run, preserving\
  \ existing behavior for non\u2011age queries."
name: accurate_age_calculation
provenance:
  action: MODIFY
  epoch: 2
  fixes: 13
  parent_version: 1
  probe_score: 9
  regressions: 2
  triggering_sample_ids:
  - task10_21
  - task2_25
  - task2_17
  - task10_13
  - task10_15
  - task9_22
  - task10_20
  - task4_26
  - task10_12
  - task8_9
  update_cycle: 1
tags: []
version: 2
---

## Accurate Age Calculation (Age‑Only Trigger)

### When to Activate
- The task description (or any user instruction) contains a case‑insensitive match for one of the following keywords/phrases: `age`, `years old`, `how old`, `what is the age`, `patient age`, `age of the patient`.
- The GET response for the patient includes a valid `birthDate` element.
- A current timestamp is available in the task context (e.g., "Current time: 2023-11-13T10:15:00+00:00").

If **any** of the above conditions are *not* met, **skip this skill** and let the default behavior proceed.

### Core Age Calculation (executed only when the trigger conditions are satisfied)
1. Extract `birthDate` from the patient resource (`entry[0].resource.birthDate`).
2. Parse the `currentTime` supplied in the task context (look for an ISO‑8601 timestamp after the word "now" or "Current time").
3. Convert both dates to year, month, and day components.
4. Compute `age = currentYear - birthYear`.
5. If `currentMonth < birthMonth` **or** (`currentMonth == birthMonth` **and** `currentDay < birthDay`), decrement `age` by 1.
6. Verify that `age` is a non‑negative integer; if negative, abort with an error message.
7. Return the age as a numeric JSON array: `FINISH([age])`.

### Fallback / Error Handling
- If `birthDate` is missing, malformed, or cannot be parsed, abort with a clear error (e.g., `FINISH(["Error: birthDate missing or invalid"])`).
- If the task context does not provide a parsable current timestamp, use the system time as a fallback but still only when the trigger condition is met.

### Output Formatting
- Always output a JSON array containing a single **integer** (no quotes). Example: `FINISH([42])`.
- Do **not** output additional narrative text or wrap the integer in quotes.

### Guard Clause (pseudocode for implementation)
```
if not re.search(r"\b(age|years old|how old|what is the age|patient age)\b", task_description, re.I):
    # Do not apply this skill
    return None
# else proceed with the steps above
```

This guard ensures the skill only runs for genuine age‑related queries, preventing interference with other tasks such as MRN look‑ups or ServiceRequest creation.
