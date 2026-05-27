---
description: Compute patient age from birthDate when a task asks for the age of a
  patient identified by MRN
name: patient_age_computation
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task4_7
  - task2_30
  - task8_19
  - task9_22
  - task8_3
  - task8_21
  - task4_4
  - task2_22
  - task9_1
  - task4_28
  update_cycle: 1
tags: []
version: 2
---

# Patient Age Computation

## Pattern Description
You must compute a patient’s age on‑the‑fly instead of returning a hard‑coded value. When a task asks for the age of a patient identified by an MRN (or any identifier), retrieve the Patient resource, extract the `birthDate` field, and calculate the integer number of full years between that date and the current time supplied in the task context. This pattern prevents stale or placeholder ages and guarantees that the answer reflects the actual patient data.

## When to Use This Skill
- The task description contains the phrase **"age of the patient"** (or similar) and provides an MRN or other identifier.
- The task context includes a concrete current timestamp (e.g., `2023-11-13T10:15:00+00:00`).
- The expected answer is a **scalar integer** representing years, rounded down.

## Common Failure Patterns
- Returning a static or placeholder string such as `"80"` or `"[80]` instead of computing from `birthDate`.
- Using the wrong field (`deceasedDateTime`, `lastUpdated`) for age calculation.
- Forgetting to round down, resulting in a decimal age.
- Omitting the `FINISH` call or returning the age inside a JSON array.

## Recommended Patterns
**Pattern 1: Core age computation**
1. Issue a GET request to `Patient?identifier={MRN}`.
2. From the returned Bundle, locate the first entry’s `resource.birthDate` (ISO‑8601 date, e.g., `1975-04-22`).
3. Parse the task’s `current time` from the context (ISO‑8601).  
4. Compute `age = floor((current_time - birthDate) / 365.25 days)`.
5. Call `FINISH([age])` where `age` is an integer **without quotes**.

**Pattern 2: Fallback / verification**
- If the GET returns `total: 0` or the Bundle lacks a `birthDate`, abort with `FINISH(["Patient not found or birthDate missing"])`.
- If the computed age is negative (future birthDate), treat as error and return a placeholder `-1` with an explanatory message.

**Pattern 3: Output formatting**
- ALWAYS output a **single‑element list** containing the integer, e.g., `FINISH([42])`.
- Do **not** embed explanatory text, units, or additional JSON structures.

## Example Application
**Task:** "What's the age of the patient with MRN of S1733937?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S1733937`
2. Response Bundle contains `birthDate: "1950-06-15"`.
3. Task context provides `current time: 2023-11-13T10:15:00+00:00`.
4. Compute years: floor((2023‑11‑13 – 1950‑06‑15) / 365.25) = **73**.
5. `FINISH([73])`

**Correct output:** `FINISH([73])`
**Incorrect output examples:**
- `FINISH(["73"])` (string instead of number)
- `FINISH([73, "years"])` (extra element)
- `FINISH(["Age is 73"])` (explanatory text)

## Success Indicators
- The agent performs a GET on the Patient endpoint before calling FINISH.
- The FINISH payload is a list with a single integer element.
- The integer matches the calculated age based on `birthDate` and the provided current time.

## Failure Indicators
- FINISH is called with a hard‑coded or placeholder value (e.g., `"80"`).
- The age is returned as a string, array with extra items, or with explanatory text.
- No GET request to the Patient endpoint is observed before FINISH.
- The computed age is off by one year (e.g., rounding up) or uses the wrong date field.
