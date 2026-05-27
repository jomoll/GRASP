---
description: Retrieve a patient MRN given full name and DOB, handling empty results
  and proper identifier extraction
name: return_mrn_if_patient_exists
provenance:
  action: ADD
  blind_select: random
  epoch: 0
  fixes_unused: 5
  probe_score_unused: 5
  regressions_unused: 3
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task4_10
  - task2_16
  - task1_11
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  update_cycle: 0
tags: []
version: 1
---

# Return MRN If Patient Exists

## Pattern Description
You must reliably obtain a patient’s Medical Record Number (MRN) when the task provides a full name and date of birth. The reusable capability is to perform a FHIR Patient search using the canonical `family` and `given` parameters (instead of the non‑standard `name` parameter), then extract the correct identifier from the returned resource. If no matching patient is found, you must return the literal string **"Patient not found"**. This pattern prevents false‑negative lookups and ensures the MRN is pulled from the proper identifier field.

## When to Use This Skill
- The instruction asks for the MRN of a patient and supplies a name (first and last) plus a birthdate, e.g., *"What’s the MRN of the patient with name Emily Hicks and DOB of 1942‑05‑11?"*.
- The task expects a single MRN string or the exact phrase **Patient not found**.
- No other clinical data (labs, observations, etc.) are required for the answer.

## Common Failure Patterns
- Using `GET /Patient?name=Full%20Name&birthdate=YYYY‑MM‑DD` which often returns an empty bundle.
- Ignoring the `total` field of the Bundle and always returning a generic "Patient not found".
- Extracting the whole Patient resource or returning the JSON bundle instead of the MRN.
- Failing to split the full name into `family` (last) and `given` (first) components.
- Not handling cases where the identifier array contains multiple entries; picking the wrong one.

## Recommended Patterns
**Pattern 1: Core lookup and extraction**
1. **Parse the full name** – split on the first space: `family = last name`, `given = first name`.
2. **Issue the GET request**:
   ```
   GET {api_base}/Patient?family={family}&given={given}&birthdate={YYYY-MM-DD}
   ```
3. **Inspect the Bundle**:
   - If `bundle.total == 0` → `FINISH(["Patient not found"])`.
   - Otherwise take the first entry (`bundle.entry[0].resource`).
4. **Extract the MRN**:
   - Prefer an identifier whose `type.coding.code` is "MR" or whose `system` contains the substring "mrn".
   - If none match, fall back to the first identifier's `value`.
5. **Return the MRN**:
   ```
   FINISH(["{mrn_value}"])
   ```

**Pattern 2: Fallback when `family/given` yields no result**
- If the primary request returns `total == 0`, optionally retry with the original `name` parameter as a last resort before concluding "Patient not found".

**Pattern 3: Output formatting**
- The FINISH payload must be a JSON array containing a single string (the MRN) or the exact phrase "Patient not found". No extra brackets, objects, or explanatory text.

## Example Application
**Task:** "What’s the MRN of the patient with name Emily Hicks and DOB of 1942‑05‑11? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Split name → `family=Hicks`, `given=Emily`.
2. GET `http://localhost:8080/fhir/Patient?family=Hicks&given=Emily&birthdate=1942-05-11`.
3. Response Bundle shows `total: 1` and entry contains:
   ```json
   "identifier": [{"value": "S2154941", "type": {"coding": [{"code": "MR"}]}}]
   ```
4. Extract `S2154941`.
5. FINISH(["S2154941"]).

**Correct output:** `FINISH(["S2154941"])`
**Incorrect output examples:**
- `FINISH(["Patient not found"])` when the bundle contains a patient.
- `FINISH([{"mrn":"S2154941"}])` (wrong JSON shape).

## Success Indicators
- The agent returns a FINISH call with a single‑element array containing either the exact MRN or the literal string "Patient not found".
- The GET request uses `family` and `given` parameters.
- The MRN value matches the `identifier.value` from the Patient resource.

## Failure Indicators
- FINISH payload contains extra text, objects, or an array with more than one element.
- The agent uses `name=` in the query and still returns "Patient not found" despite the patient existing.
- The returned string is the full Patient JSON or includes the word "Patient" with additional description.
