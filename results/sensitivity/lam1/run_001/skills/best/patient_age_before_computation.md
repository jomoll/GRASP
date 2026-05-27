---
description: "Ensures a Patient GET is performed and birthDate extracted before computing\
  \ age **only when the task explicitly asks for the patient\u2019s age** (e.g., the\
  \ task description contains the word \"age\" or phrases like \"how old\" together\
  \ with a patient identifier). This guard prevents the pattern from interfering with\
  \ unrelated patient operations such as MRN lookup, referral creation, or other non\u2011\
  age queries.\n\n## When to Use This Skill\n- The task description asks for the age\
  \ of a patient, e.g., \"What is the age of the patient with MRN X?\" or \"How old\
  \ is patient Y?\".\n- The task provides a current timestamp in the context (e.g.,\
  \ `2023-11-13T10:15:00+00:00`).\n- No patient resource has been retrieved yet in\
  \ the current execution trace.\n\n## Guard Clause\n- If the task description does\
  \ **not** contain the keyword \"age\" (case\u2011insensitive) or a phrase indicating\
  \ an age request, the skill is ignored.\n- If the task already includes a `GET /Patient`\
  \ request before any age computation, the skill does not enforce an additional GET.\n\
  \n## Recommended Patterns (unchanged)\n**Pattern 1: Resolve patient first**\n1.\
  \ Issue `GET {api_base}/Patient?identifier={MRN}` where `{MRN}` is the identifier\
  \ from the task.\n2. Verify the response is a `Bundle` with `total >= 1` and an\
  \ entry whose `resource.birthDate` exists.\n3. Extract `birthDate` (ISO\u20118601\
  \ date string) from the first entry.\n\n**Pattern 2: Compute age**\n1. Parse the\
  \ `birthDate` and the current time supplied in the task context.\n2. Compute the\
  \ difference in years, rounding down (i.e., floor).\n3. Store the result as an integer\
  \ `age`.\n\n**Pattern 3: Return result**\n- If a patient was found, `FINISH([age])`\
  \ where `age` is the integer.\n- If no patient was found (`total == 0`), `FINISH([\"\
  Patient not found\"])`.\n\n## Success Indicators\n- A `GET` request to the Patient\
  \ endpoint appears **only** for age\u2011related tasks before any age calculation.\n\
  - The final `FINISH` payload is a JSON array containing a single integer (or the\
  \ string \"Patient not found\").\n\n## Failure Indicators\n- The skill fires for\
  \ tasks that do not request age, leading to mismatched `FINISH` payloads.\n- No\
  \ Patient GET request is present before the `FINISH` for an age\u2011related task.\n\
  - The `FINISH` payload contains free\u2011text or a non\u2011integer value for an\
  \ age request."
name: patient_age_before_computation
provenance:
  action: ADD
  epoch: 0
  fixes: 12
  probe_score: 13
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task9_14
  - task9_27
  - task1_12
  update_cycle: 0
tags: []
version: 1
---

# Patient Age Retrieval Before Computation

## Pattern Description
You must always resolve a patient record before attempting to calculate the patient’s age. The reusable pattern is: when a task asks for the age of a patient identified by an MRN (or any identifier), first query the FHIR Patient endpoint, extract the `birthDate` field, compute the age using the current time supplied in the task context, and return the integer age. This prevents assumptions about the patient’s existence and guarantees the correct field is used.

## Guard Clause (When **not** to apply)
- If the task description does **not** contain the word "age" (case‑insensitive) or a phrase indicating an age request (e.g., "how old", "years old"), this skill should be ignored.
- If the execution trace already includes a `GET /Patient` request before any age computation, the skill does not enforce an additional GET.

## When to Use This Skill
- Task description: "What’s the age of the patient with MRN of X?" (or any identifier‑based age request).
- The task provides a current timestamp in the context (e.g., `2023-11-13T10:15:00+00:00`).
- No patient resource has been retrieved yet in the current execution trace.

## Common Failure Patterns
- Agent replies with reasoning but never issues a `GET /Patient?identifier=...` request.
- Agent attempts to compute age using a hard‑coded value or a field other than `birthDate` (e.g., `effectiveDateTime`).
- Agent returns a free‑text sentence instead of a JSON array with a single integer.
- Agent proceeds to `FINISH` without confirming that the Patient bundle contains an entry.

## Recommended Patterns
**Pattern 1: Resolve patient first**
1. Issue `GET {api_base}/Patient?identifier={MRN}` where `{MRN}` is the identifier from the task.
2. Verify the response is a `Bundle` with `total >= 1` and an entry whose `resource.birthDate` exists.
3. Extract `birthDate` (ISO‑8601 date string) from the first entry.

**Pattern 2: Compute age**
1. Parse the `birthDate` and the current time supplied in the task context.
2. Compute the difference in years, rounding down (i.e., floor).
3. Store the result as an integer `age`.

**Pattern 3: Return result**
- If a patient was found, `FINISH([age])` where `age` is the integer.
- If no patient was found (`total == 0`), `FINISH(["Patient not found"])`.

## Example Application
**Task:** "What's the age of the patient with MRN of S2863714?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2863714`
2. Response contains `entry[0].resource.birthDate = "1975-04-22"`.
3. Current time from context: `2023-11-13T10:15:00+00:00`.
4. Compute age: 2023‑1975 = 48 (birthday already passed this year, so floor = 48).
5. `FINISH([48])`.

**Incorrect output example:** `FINISH(["Patient is 48 years old."])` – wrong format.

## Success Indicators
- A `GET` request to the Patient endpoint appears in the action log before any age calculation.
- The response is inspected for `birthDate`.
- The final `FINISH` payload is a JSON array containing a single integer (or the string "Patient not found").

## Failure Indicators
- No Patient GET request is present before the `FINISH`.
- The `FINISH` payload contains free‑text or a non‑integer value.
- The agent attempts to compute age without confirming the patient exists.
