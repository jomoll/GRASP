---
description: Compute patient age only after confirming a valid birthDate field exists
name: age_calculation_with_birthdate_validation
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 5
  regressions: 2
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task5_15
  - task9_8
  - task4_10
  - task2_16
  - task1_11
  - task2_14
  - task9_14
  - task10_20
  update_cycle: 0
tags: []
version: 1
---

# AgeCalculationWithBirthdateValidation

## Pattern Description
You must calculate a patient’s age **only** after you have successfully retrieved a Patient resource that contains a valid `birthDate` element. This prevents returning hard‑coded or stale ages and ensures the agent gracefully handles missing or malformed data.

## When to Use This Skill
- When the instruction asks for the age of a patient identified by an MRN (e.g., `What’s the age of the patient with MRN of S123456?`).
- The task context provides a current timestamp (e.g., `2023-11-13T10:15:00+00:00`).
- The answer must be an integer rounded down.

## Common Failure Patterns
- Returning a static integer without inspecting the `birthDate` field.
- Ignoring a `Bundle` with `total: 0` (patient not found) and still outputting an age.
- Using a missing or malformed `birthDate` value, which can cause runtime errors.

## Recommended Patterns
**Pattern 1: Retrieve and validate the Patient resource**
1. Issue a GET request:
   ```
   GET http://localhost:8080/fhir/Patient?identifier={MRN}
   ```
2. Verify the response bundle:
   - `total` must be `1` (or >0). If `total == 0`, FINISH(["Patient not found"]).
   - Locate the patient resource at `entry[0].resource`.
3. Extract `birthDate`:
   - If the field is missing or empty, FINISH(["Patient birth date unavailable"]).
   - Ensure the value matches the ISO‑8601 date format (`YYYY-MM-DD`).

**Pattern 2: Compute the age**
1. Parse the `birthDate` and the current time provided in the task context (or use `2023-11-13T10:15:00+00:00` if not supplied).
2. Calculate the difference in years, rounding down:
   ```python
   age = current_date.year - birth_date.year - ((current_date.month, current_date.day) < (birth_date.month, birth_date.day))
   ```
3. Return the age as a plain integer string:
   ```
   FINISH(["{age}"])
   ```

**Pattern 3: Fallback handling**
- If any step fails (network error, unexpected JSON shape, parsing error), respond with a clear diagnostic message rather than a guessed number, e.g., `FINISH(["Unable to determine age due to missing birthDate."])`.

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. Response bundle shows `total: 1` and contains:
   ```json
   {"resourceType":"Patient","id":"S2874099","birthDate":"1963-04-22"}
   ```
3. Extract `birthDate = 1963-04-22`.
4. Current time from context: `2023-11-13T10:15:00+00:00` → date `2023-11-13`.
5. Compute age:
   - Years diff = 2023 - 1963 = 60.
   - Since 11‑13 is after 04‑22, no subtraction needed → age = 60.
6. Return:
   ```
   FINISH(["60"])
   ```

## Success Indicators
- The agent returns an integer that matches a manual age calculation.
- No `FINISH` output contains placeholder numbers when the patient or birthDate is missing.
- The agent logs a clear "Patient not found" or "birth date unavailable" message when appropriate.

## Failure Indicators
- The agent outputs a hard‑coded age without performing the GET request.
- The agent returns an age even when the bundle `total` is 0.
- The agent crashes or returns a non‑numeric string because `birthDate` was missing or malformed.
