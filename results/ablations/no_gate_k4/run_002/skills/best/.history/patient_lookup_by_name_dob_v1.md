---
description: "Lookup a patient\u2019s MRN using family/given name and birthdate, verify\
  \ bundle entries before answering"
name: patient_lookup_by_name_dob
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
- patient
- lookup
- mrn
version: 1
---

# Patient Lookup by Name and DOB

## Pattern Description
You must locate a patient when the task provides a full name (first and last) and a date of birth. The reliable FHIR search uses separate `family` and `given` query parameters together with `birthdate`. After the GET, always inspect the returned Bundle for at least one `entry`. If an entry exists, extract the patient’s MRN from the first identifier (or the identifier whose `system` matches the MRN system if known). If no entry is present, answer exactly **"Patient not found"**. This prevents false‑negative answers caused by using the `name` parameter, which many servers treat as a free‑text search and may return zero results even when the patient exists.

## When to Use This Skill
- Task asks: "What’s the MRN of the patient with name **X Y** and DOB **YYYY‑MM‑DD**?"  
- Any instruction that requires you to verify a patient’s existence before proceeding with further actions (e.g., ordering labs, recording vitals).

## Common Failure Patterns
- Using `GET .../Patient?name=First%20Last&birthdate=...` → `total: 0` even though patient exists.
- Skipping the check of `bundle.entry` and immediately returning "Patient not found".
- Extracting the MRN from the wrong field (e.g., `id` instead of `identifier.value`).

## Recommended Patterns
**Pattern 1: Build the correct search URL**
1. Split the full name into `family` (last) and `given` (first) components.
2. Issue:
   ```
   GET {api_base}/Patient?family={family}&given={given}&birthdate={YYYY-MM-DD}
   ```
3. Ensure `&_format=json` is added if required by the server.

**Pattern 2: Verify the response bundle**
1. Parse the JSON response.
2. If `bundle.total == 0` **or** `bundle.entry` is missing/empty → `FINISH(["Patient not found"])`.
3. Otherwise, take the first entry:
   ```json
   patient = bundle.entry[0].resource
   ```

**Pattern 3: Extract the MRN**
1. Look for an identifier with a known MRN system (e.g., `http://hospital.org/mrn`). If none, fall back to the first identifier.
2. MRN = `identifier.value` (as a plain string, no list).
3. Return:
   ```
   FINISH(["{MRN}"])
   ```

## Example Application
**Task:** "What’s the MRN of the patient with name Julie Rodriguez and DOB of 1962-01-20? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Split name → family=`Rodriguez`, given=`Julie`.
2. GET `http://localhost:8080/fhir/Patient?family=Rodriguez&given=Julie&birthdate=1962-01-20`.
3. Parse response. Suppose `bundle.total` is 1 and `bundle.entry[0].resource.identifier[0].value` = `S1234567`.
4. Extract MRN = `S1234567`.
5. FINISH(["S1234567"]).

**If the bundle had `total: 0`** → FINISH(["Patient not found"]).

## Success Indicators
- The agent builds the URL with `family` and `given` parameters.
- The agent checks `bundle.total` / `bundle.entry` before deciding.
- The returned MRN is a plain string inside a JSON list, matching the identifier value.

## Failure Indicators
- The agent uses `name=` instead of `family`/`given`.
- The agent returns "Patient not found" while `bundle.total > 0`.
- The agent includes extra explanatory text or wraps the MRN in an object instead of a scalar string.
