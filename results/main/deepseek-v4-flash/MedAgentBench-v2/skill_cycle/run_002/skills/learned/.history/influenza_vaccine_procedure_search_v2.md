---
description: Search Procedure resource for influenza vaccine records using CPT code
  90686
name: influenza_vaccine_procedure_search
provenance:
  action: MODIFY
  epoch: 2
  fixes: 2
  parent_version: 1
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task10_24
  - task4_23
  - task2_25
  - task9_22
  - task4_28
  - task9_1
  - task1_11
  - task2_30
  - task3_7
  - task2_14
  update_cycle: 0
tags: []
version: 2
---

# Influenza Vaccine Procedure Search with Fallback Verification

## Pattern Description

This skill provides a strategy for searching the FHIR Procedure resource to find influenza vaccine administration records using CPT code 90686. The central lesson is that when a search returns zero results, you must not immediately conclude the vaccine was never administered or that it has expired. Instead, you must verify the search was complete by checking for paginated results, considering alternative date ranges, and confirming the patient identifier is correct before making a decision.

When searching for influenza vaccine records, you must treat an empty search result as an incomplete signal that requires additional verification steps before concluding the vaccine is absent. The correct behavior is to first exhaust all reasonable search strategies, then only conclude absence if all searches return empty.

## When to Use This Skill

- When a GET /Procedure search for influenza vaccine (CPT 90686) returns `"total": 0` or an empty `entry` array
- When the task requires determining the date of the last influenza vaccine to decide if a new one should be ordered
- When the task context specifies a CPT code for influenza vaccine and a patient identifier
- When the current date is provided and you need to calculate if more than 365 days have passed since the last vaccine

## Common Failure Patterns

- Assuming an empty search result means the vaccine was never given, when the search may have been too narrow (wrong date range, wrong code, pagination)
- Not checking for paginated results when the bundle has a `link` with `relation` of `"next"` — the agent must follow pagination links to get all results
- Using only the CPT code 90686 without considering that influenza vaccines may be recorded under other codes (e.g., CVX codes like 150, 158, 161, or other CPT codes like 90688, 90685)
- Failing to verify the patient identifier is correct before concluding absence
- Immediately ordering a new vaccine when no record is found, without confirming the search was exhaustive

## Recommended Patterns

**Pattern 1: Primary search with correct parameters**
1. Issue GET to `/Procedure?patient={patientId}&code=90686&date=ge{date-5years}`
   - Use a broad date range (at least 5 years back from current date) to capture all possible records
   - The date parameter should use `ge` (greater than or equal) with a date far enough back to catch any vaccine
2. Check the response bundle for `total` field and `entry` array
3. If `total > 0`, extract the most recent `Procedure.performedDateTime` or `Procedure.performedPeriod.end`

CORRECT: `GET /Procedure?patient=S1777769&code=90686&date=ge2019-01-09` (5 years back)
WRONG:   `GET /Procedure?patient=S1777769&code=90686&date=ge2023-01-09` (only 1 year back, may miss older records)

**Pattern 2: Fallback when primary search returns zero results**
1. Check the response bundle for pagination links — if `link` array contains an entry with `"relation": "next"`, follow that URL to get the next page
2. If still no results, try alternative codes:
   - CVX codes: 150 (influenza, injectable), 158 (influenza, nasal), 161 (influenza, high dose)
   - Other CPT codes: 90688, 90685, 90687, 90689, 90756
3. If alternative codes also return empty, try searching without the `code` parameter to see if any Procedure records exist for this patient at all
4. Only after all these searches return empty should you conclude no vaccine record exists

**Pattern 3: Decision and action rule**
1. If a vaccine record is found, extract the most recent `performedDateTime`
2. Calculate days since that date using the current time provided in the task context
3. If more than 365 days have passed (or no record found after exhaustive search), order a new influenza vaccine
4. When ordering, use the correct medication code and format for MedicationRequest

CORRECT output when no vaccine found after exhaustive search: `FINISH(["No influenza vaccine found for patient S1777769 after exhaustive search. Since no vaccine was found, it has been more than 365 days since the last dose. Ordering a new influenza vaccine for today."])`
WRONG output: `FINISH(["No influenza vaccine found for patient S1777769. Since no vaccine was found, it has been more than 365 days since the last dose. Ordering a new influenza vaccine for today."])` (missing verification steps)

## Example Application

**Task:** "Determine the date of the last influenza vaccine for patient S1777769. If it was administered more than 365 days ago, order a new influenza vaccine for today. It's 2024-01-09T00:00:00+00:00 now. The CPT code for influenza vaccine is 90686."

**Step-by-step:**

1. Issue GET with broad date range:
   `GET /Procedure?patient=S1777769&code=90686&date=ge2019-01-09`
   
2. Response shows `"total": 0` — empty result.

3. Check for pagination: No `"next"` link in the response.

4. Try alternative codes:
   - `GET /Procedure?patient=S1777769&code=150&date=ge2019-01-09` (CVX code)
   - `GET /Procedure?patient=S1777769&code=90688&date=ge2019-01-09` (alternative CPT)
   
5. If all searches return empty, then conclude no vaccine record exists.

6. Since no vaccine was found, it has been more than 365 days since the last dose. Order a new vaccine:
   - POST to `/MedicationRequest` with:
     - `medicationCodeableConcept.coding[0].system = "http://hl7.org/fhir/sid/ndc"`
     - `medicationCodeableConcept.coding[0].code = "90686"`
     - `medicationCodeableConcept.coding[0].display = "Influenza vaccine (quadrivalent, preservative-free, IM)"`
     - `authoredOn = "2024-01-09T00:00:00+00:00"`
     - `status = "active"`
     - `intent = "order"`
     - `subject.reference = "Patient/S1777769"`

CORRECT output: `FINISH(["No influenza vaccine found for patient S1777769 after exhaustive search. Since no vaccine was found, it has been more than 365 days since the last dose. Ordering a new influenza vaccine for today."])`
WRONG output: `FINISH(["No influenza vaccine found for patient S1777769. Since no vaccine was found, it has been more than 365 days since the last dose. Ordering a new influenza vaccine for today."])`

## Success Indicators

- Agent performs at least one fallback search (alternative code or broader date range) when primary search returns empty
- Agent checks for pagination links in the response bundle before concluding absence
- Agent explicitly states that the search was exhaustive before concluding no vaccine exists
- Agent correctly extracts `performedDateTime` from the most recent Procedure entry when results are found
- Agent correctly calculates days since last vaccine and makes appropriate decision

## Failure Indicators

- Agent immediately concludes "no vaccine found" after a single search without fallback verification
- Agent orders a new vaccine without confirming the search was complete
- Agent uses a date range that is too narrow (e.g., only 1 year back) and misses older records
- Agent does not check for pagination when the bundle has a `"next"` link
- Agent extracts the wrong date field (e.g., `recordedDate` instead of `performedDateTime`)
