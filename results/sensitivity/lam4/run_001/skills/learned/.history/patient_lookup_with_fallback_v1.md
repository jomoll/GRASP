---
description: Robustly find a patient MRN using primary and fallback FHIR search parameters
  when the first query returns no results.
name: patient_lookup_with_fallback
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 6
  regressions: 3
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task5_20
  - task1_6
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task9_14
  - task9_27
  update_cycle: 0
tags:
- patient_lookup
- fallback
- FHIR
version: 1
---

# Patient Lookup with Fallback

## Pattern Description
You must retrieve a patient’s MRN (identifier) from the FHIR server even when the initial search yields no matches. The core capability is a two‑stage lookup: first try the most specific query (full name + birthdate). If that returns an empty Bundle, automatically fall back to alternative query patterns that are still precise enough to avoid false positives (e.g., split name into family/given, search by identifier, or use fuzzy name matching). This prevents false‑negative "Patient not found" answers.

## When to Use This Skill
- When a task asks for the MRN of a patient given a full name and DOB.
- When the initial `GET /Patient?name=...&birthdate=...` returns `total: 0`.
- When the task requires the MRN even if the patient exists under a different name representation (e.g., middle name, nickname) or only an identifier is known.

## Common Failure Patterns
- `total: 0` from the primary search but the patient actually exists → false‑negative answer.
- Using only the `name` parameter which may not match the server’s indexing (some servers require `family`/`given`).
- Ignoring the `identifier` search when the MRN is provided in the request context.
- Returning "Patient not found" without attempting a fallback query.

## Recommended Patterns
**Pattern 1: Primary precise search**
1. Build the URL `GET {base}/Patient?name={full_name}&birthdate={dob}` where `full_name` is URL‑encoded.
2. Inspect the returned Bundle’s `total` field.
   - **CORRECT**: `total > 0` → extract the first entry’s `identifier` where `type.coding.code == "MR"` (or the first identifier if type unknown).
   - **WRONG**: Assume `total == 0` means the patient does not exist.

**Pattern 2: Fallback to split name search**
1. Split the full name into `family` (last) and `given` (first) components.
2. Issue `GET {base}/Patient?family={family}&given={given}&birthdate={dob}`.
3. If `total > 0`, extract the MRN as above.

**Pattern 3: Fallback to identifier search**
1. If the task context already contains an MRN or identifier string, try `GET {base}/Patient?identifier={identifier}`.
2. If a match is found, use that MRN directly.

**Pattern 4: Final fallback – fuzzy name search**
1. Use `GET {base}/Patient?name={family}` (family only) as a last resort.
2. If exactly one entry matches and the birthdate matches, accept it; otherwise, do not guess.

**Pattern 5: Answer construction**
- If any fallback succeeds, `FINISH(["{MRN}"])`.
- If all attempts fail, `FINISH(["Patient not found"])`.

## Example Application
**Task:** "What’s the MRN of the patient with name Andrew Bishop and DOB of 1963-01-29? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?name=Andrew%20Bishop&birthdate=1963-01-29`
2. Response Bundle `total: 0` → primary search failed.
3. Split name: family=`Bishop`, given=`Andrew`.
4. `GET http://localhost:8080/fhir/Patient?family=Bishop&given=Andrew&birthdate=1963-01-29`
5. Suppose this returns `total: 1` with entry containing `identifier: [{"value":"S1234567"}]`.
6. Extract MRN `S1234567`.
7. `FINISH(["S1234567"])`.

If step 4 also returned `total: 0`, proceed to identifier fallback (if an identifier is known) or final fuzzy search, then answer accordingly.

## Success Indicators
- The agent performs at least two GET requests when the first returns `total: 0`.
- The final FINISH output contains a valid MRN string when the patient exists, or the exact phrase "Patient not found" when no matches are found after all fallbacks.

## Failure Indicators
- The agent returns "Patient not found" after only the primary query, even though a later fallback would have succeeded.
- The agent extracts the MRN from the wrong field (e.g., uses `id` instead of `identifier.value`).
- The agent issues no fallback queries when `total: 0`.
