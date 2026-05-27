---
description: Generate FINISH output after a single GET request by extracting needed
  fields and handling empty results
name: answer_generation_from_single_get
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task3_14
  update_cycle: 0
tags:
- answer_generation
- post_get_processing
- fallback_handling
version: 1
---

# Answer Generation from Single FHIR GET Response

## Pattern Description
You must turn the raw JSON returned from a single `GET` request into the final answer for the user. This skill applies when the task only requires reading a resource (e.g., a Patient, Observation, or MedicationRequest) and reporting a value, an identifier, or a date. The agent should inspect the response bundle, extract the required element, apply any simple conditional logic (e.g., age calculation, date comparison, "not found" handling), and then emit a `FINISH` action with the exact format the task expects.

## When to Use This Skill
- When the user asks for a single piece of information that lives in a FHIR resource (MRN, age, latest lab value, observation date, etc.)
- After you have issued a `GET` request and received a Bundle response
- When the task does **not** require creating or updating resources, only reporting data
- When the response may be empty (resource not found) and the task specifies a fallback answer such as "Patient not found"

## Common Failure Patterns
- Agent issues the `GET` request but never emits a `FINISH` action, leaving the conversation hanging
- Agent extracts the wrong field (e.g., uses `effectiveDateTime` instead of `issued` for lab results)
- Agent treats the whole Bundle as a string and returns it verbatim
- Empty Bundle is not detected, leading to missing "not found" answer
- Numeric values are returned with units inside the string (e.g., `"3.5 mmol/L"` instead of `3.5`)

## Recommended Patterns
**Pattern 1: Core extraction and answer construction**
1. Parse the JSON response. Verify that `resourceType` is `Bundle` and `total` > 0.
2. Locate the first entry (`response.entry[0].resource`).
3. Extract the exact field required by the task:
   - MRN: `resource.identifier` where `type.coding.code == "MR"` → `identifier.value`
   - Observation value: `resource.valueQuantity.value` (numeric) **or** `resource.valueString` (for BP, free‑text)
   - Observation date: `resource.effectiveDateTime` (or `issued` if present)
   - Patient birthdate: `resource.birthDate`
4. Apply any simple logic:
   - Age: `floor((now - birthDate) / 365.25)`
   - Date older than 1 year: compare ISO‑8601 strings or convert to datetime objects
5. Format the answer exactly as the task expects and emit:
   ```
   FINISH(["<answer>"])
   ```
   Example correct output: `FINISH(["HbA1c 7.2% recorded on 2023-09-10"])`

**Pattern 2: Empty‑result fallback**
1. After parsing the Bundle, if `total == 0` (or `entry` missing), use the fallback string supplied in the instruction (e.g., "Patient not found").
2. Emit `FINISH(["Patient not found"])`.

**Pattern 3: Unit‑clean extraction**
- If the value is a string containing a number and a unit, split on whitespace and keep only the numeric part for numeric comparisons, but retain the unit in the final user‑facing answer if the task asks for it.

## Example Application
**Task:** "What’s the MRN of the patient with name Margaret Kidd and DOB of 1982-08-24? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?family=Kidd&given=Margaret&birthdate=1982-08-24`
2. Parse the returned Bundle. `total == 1` → proceed.
3. Locate `entry[0].resource.identifier` where `type.coding.code == "MR"` and read `value` → `S0789363`.
4. Construct answer: `FINISH(["S0789363"])`.

**Correct output:** `FINISH(["S0789363"])`
**Wrong output:** `FINISH(["{"resourceType":"Bundle",...}"])`

## Success Indicators
- After a `GET` request the agent immediately follows with a `FINISH` containing the extracted value in the exact format required.
- Empty bundles trigger the specified fallback answer.
- Numeric comparisons (e.g., age, date > 1 year) are performed correctly before answering.

## Failure Indicators
- The agent returns only the `GET` action and stops.
- The `FINISH` payload contains raw JSON or the wrong field.
- No fallback is used when the bundle is empty.
- Units are incorrectly concatenated with numeric values.
