---
description: Add age extraction handling to patient lookup skill
name: patient_lookup_with_fallback
provenance:
  action: MODIFY
  epoch: 3
  fixes: 9
  parent_version: 1
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task1_16
  - task10_24
  - task9_5
  - task2_14
  - task10_20
  - task3_27
  - task10_13
  - task10_17
  - task10_27
  - task9_22
  update_cycle: 0
tags: []
version: 2
---

# Patient Lookup with Fallback

## Pattern Description
You must reliably locate a patient resource before any downstream operation that depends on patient data. The core strategy is to query the FHIR server using the most specific identifier (MRN) and, if that returns no results, fall back to broader search parameters (name, birthdate, etc.). This skill also covers the common sub‑task of computing a patient’s age from the `birthDate` field when the task explicitly asks for the age.

## When to Use This Skill
- When a task references a patient by MRN and expects any patient‑related information (e.g., age, demographics, or linking observations).
- When a task asks for the patient’s age directly (e.g., “What’s the age of the patient with MRN S123456?”).
- When the primary `identifier` search returns an empty bundle and the task still requires a patient resource.

## Common Failure Patterns
- No GET request is issued for the patient before trying to compute age.
- The agent extracts `birthDate` from the wrong element (e.g., from a related `Condition` instead of the `Patient`).
- Age is calculated using the current system time instead of the task‑provided `Current time` context, leading to off‑by‑one‑day errors.
- The agent proceeds with downstream logic (e.g., ordering labs) without confirming that a patient resource was actually retrieved.

## Recommended Patterns
**Pattern 1: Primary patient lookup**
1. Issue `GET {api_base}/Patient?identifier={MRN}`.
2. If the bundle `total` > 0, extract the first entry’s `resource`.
3. Store the patient reference (e.g., `Patient/{id}`) for later use.

**Pattern 2: Fallback lookup** (only if Pattern 1 returned `total` = 0)
1. Construct a secondary query using any known demographic fields, e.g.: `GET {api_base}/Patient?name={fullName}&birthdate={DOB}` or split into `family`/`given` parameters.
2. If this bundle also returns no results, abort the task with an appropriate message (e.g., `FINISH(["Patient not found"])`).

**Pattern 3: Age extraction (new)**
1. After a successful patient retrieval (Pattern 1 or 2), read the `birthDate` field (ISO‑8601 date string).
2. Parse the `Current time` value supplied in the task context (e.g., `2023-11-13T10:15:00+00:00`).
3. Compute the age as the integer number of full years between `Current time` and `birthDate` (round down).
4. Return the age with `FINISH([age])`.

**Pattern 4: Formatting / completion rule**
- Always output a JSON‑compatible array inside `FINISH`, e.g., `FINISH([51])` for an age of 51.
- Do **not** embed explanatory text or units; the caller expects a plain numeric value.

## Example Application
**Task:** "What's the age of the patient with MRN of S2823623?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2823623`
2. Bundle `total` = 1 → extract `entry[0].resource.birthDate` = `1972-04-15`.
3. Task context provides `Current time = 2023-11-13T10:15:00+00:00`.
4. Compute age: 2023 − 1972 = 51 (birthday already passed in 2023), so age = 51.
5. `FINISH([51])`

**Correct output:** `FINISH([51])`
**Incorrect output examples:**
- `FINISH(["51 years"])` – wrong type.
- `FINISH([51.0])` – float instead of integer.

## Success Indicators
- A GET request for the patient is always present before any age‑related computation.
- The `birthDate` field is read from the patient resource, not from other resources.
- The final `FINISH` payload contains a single integer inside an array.

## Failure Indicators
- No patient GET request appears before the age calculation.
- The agent uses the system clock instead of the task‑provided `Current time`.
- The output includes text, units, or a non‑integer type.
- The agent proceeds to order labs or other actions without confirming a patient was found.
