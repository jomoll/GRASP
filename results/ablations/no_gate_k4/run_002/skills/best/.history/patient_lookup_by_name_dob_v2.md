---
description: Add strict verification of name and birthDate before returning MRN
name: patient_lookup_by_name_dob
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task1_27
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_26
  - task4_6
  - task4_27
  update_cycle: 0
tags: []
version: 2
---

# Patient Lookup By Name and DOB with Verification

## Pattern Description
You must look up a patient by family name, given name, and birthDate, but you also need to **verify** that the returned Patient resource actually matches those exact values before returning the MRN. This prevents false‑positive matches when the FHIR server returns a placeholder or mismatched record.

## When to Use This Skill
- When a task asks: "What’s the MRN of the patient with name **X Y** and DOB **YYYY‑MM‑DD**? If the patient does not exist, answer **Patient not found**."
- Whenever you have performed a `GET /Patient` search with `family`, `given`, and `birthdate` parameters.

## Common Failure Patterns
- The search bundle has `total = 1` but the contained Patient’s `name` or `birthDate` does **not** exactly match the query (e.g., different spelling, missing fields).
- The bundle contains a placeholder patient that does not correspond to the requested identity, leading to an incorrect MRN being returned.
- The bundle is empty (`total = 0`) and the skill still returns an MRN.

## Recommended Patterns
**Pattern 1: Core lookup and verification**
1. Issue the GET request:
   ```
   GET {api_base}/Patient?family={family}&given={given}&birthdate={birthdate}
   ```
2. Parse the response as a Bundle.
3. If `bundle.total == 0` → `FINISH("Patient not found")`.
4. Extract the first entry’s `resource` (a Patient).
5. Verify:
   - `resource.birthDate` equals the requested `birthdate` (string compare).
   - `resource.name` array contains at least one element where:
     - `family` (case‑insensitive) equals the requested family name.
     - `given` array contains a value that case‑insensitively equals the requested given name.
6. If any verification fails → `FINISH("Patient not found")`.
7. Otherwise, locate the MRN:
   - Look for an identifier with `type.coding.code == "MR"` or similar, or use the `id` if the system encodes MRN as the resource ID.
   - Return the MRN as a **scalar string**: `FINISH("S1234567")`.

**Pattern 2: Fallback handling**
- If the bundle contains multiple entries, repeat steps 5‑6 for each until a matching patient is found; if none match, return "Patient not found".

**Pattern 3: Output formatting**
- Ensure the final `FINISH` payload is a single string, not an array or object. The `verify_before_finish` skill will enforce this, but you must still output a scalar.

## Example Application
**Task:** "What’s the MRN of the patient with name **Emily Hicks** and DOB of **1942‑05‑11**? If the patient does not exist, answer **Patient not found**."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?family=Hicks&given=Emily&birthdate=1942-05-11`
2. Response Bundle has `total = 1`.
3. Extract `patient = bundle.entry[0].resource`.
4. Verify:
   - `patient.birthDate == "1942-05-11"` ✅
   - `patient.name[0].family.lower() == "hicks"` ✅
   - `"Emily"` is in `patient.name[0].given` ✅
5. Find MRN identifier (e.g., `patient.identifier[0].value == "S2154941"`).
6. `FINISH("S2154941")`.

If step 4 failed, you would instead `FINISH("Patient not found")`.

## Success Indicators
- The agent returns a single MRN string **only** when the patient’s name and birthDate exactly match the query.
- When no matching patient exists, the agent returns the literal string `Patient not found`.
- The `verify_before_finish` skill confirms the output is a scalar string.

## Failure Indicators
- The agent returns an MRN despite a mismatch in name or birthDate.
- The agent returns an array, object, or extra explanatory text instead of a scalar string.
- The agent does not check the bundle’s `total` field before extracting a patient.
