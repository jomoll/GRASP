---
description: When a code-based vaccine search returns no results, retry with medication
  name text search
name: vaccine_search_fallback_by_name
provenance:
  action: ADD
  epoch: 3
  fixes: 5
  probe_score: 1
  regressions: 4
  triggering_sample_ids:
  - task3_16
  - task9_9
  - task10_15
  - task3_7
  - task1_7
  - task3_3
  - task4_21
  - task1_6
  - task8_23
  - task3_10
  update_cycle: 1
tags: []
version: 1
---

# Vaccine Search Fallback by Medication Name

## Pattern Description

When searching for vaccine administration records (e.g., influenza vaccine, COVID-19 vaccine) using a CPT code returns zero results, the vaccine may be stored in the FHIR server with a different coding system or without the expected code. In such cases, you must retry the search using the medication name as a text parameter to find records that may have been stored with alternative codes or without structured coding.

This skill teaches a two-phase search strategy: first search by the known code, and if that returns empty, immediately retry using the medication name as a text search parameter. This prevents false negatives where the agent incorrectly concludes a vaccine was never administered when it was simply stored differently.

## When to Use This Skill

- When a GET /Procedure or GET /MedicationRequest search using a specific CPT code (e.g., `code=90686` for influenza vaccine) returns `"total": 0`
- When the task involves checking for prior vaccination history before ordering a new vaccine
- When the task provides both a CPT code and a medication name (e.g., "influenza vaccine (quadrivalent, preservative-free, IM)")
- When searching for COVID-19 vaccination records where the code may not match the stored representation

## Common Failure Patterns

- Searching only by CPT code `90686` and concluding no influenza vaccine was ever given, when the record exists with a different code or no code
- Searching only by `code=COVIDVACCINE` and missing records stored under alternative codes like `91320` or `207`
- Using `medication` parameter on MedicationRequest when the vaccine was recorded as a Procedure resource
- Failing to use the `text` search parameter on Procedure to match by name when code search fails
- Concluding "no vaccine found" and immediately ordering a new one without exhausting all search strategies

## Recommended Patterns

**Pattern 1: Two-phase code-then-name search for Procedures**
1. First, search Procedure with the known CPT code: `GET /Procedure?patient={id}&code={cpt_code}`
2. If the response has `"total": 0`, immediately retry using the medication name as a text search: `GET /Procedure?patient={id}&_text={vaccine_name}`
3. Use the name exactly as provided in the task (e.g., "influenza vaccine", "COVID-19 vaccine")
4. If the text search also returns empty, then conclude no prior vaccine exists

CORRECT: `GET /Procedure?patient=S1891852&code=90686` → empty → `GET /Procedure?patient=S1891852&_text=influenza%20vaccine`
WRONG:   `GET /Procedure?patient=S1891852&code=90686` → empty → FINISH("No vaccine found")

**Pattern 2: Two-phase search for MedicationRequests**
1. First, search MedicationRequest with the medication name: `GET /MedicationRequest?patient={id}&medication={name}`
2. If empty, try alternative name variations (e.g., "COVID-19 VAC", "COVIDVACCINE", "COVID-19")
3. If still empty, search Procedure with the code as fallback

**Pattern 3: Verification before ordering**
- Only order a new vaccine after you have exhausted both code-based and name-based searches
- If any search returns results, extract the most recent `performedDateTime` or `authoredOn` to determine if a new dose is needed
- Do not order a vaccine if a prior administration exists within the required time window

## Example Application

**Task:** "Determine the date of the last influenza vaccine for patient S1891852. If it was administered more than 365 days ago, order a new influenza vaccine for today."

**Step-by-step:**

1. Issue initial code-based search: `GET /Procedure?patient=S1891852&code=90686`
2. Response: `{ "total": 0 }` — no results with CPT code 90686
3. Apply fallback: `GET /Procedure?patient=S1891852&_text=influenza%20vaccine`
4. Response: `{ "total": 1, "entry": [{ "resource": { "performedDateTime": "2020-03-15", ... } }] }`
5. Extract `performedDateTime`: "2020-03-15"
6. Calculate days since last vaccine: from 2020-03-15 to 2024-01-09 is > 365 days
7. Order new vaccine: `POST /MedicationRequest` with appropriate details

CORRECT output: `FINISH(["Last influenza vaccine was 2020-03-15 (>365 days ago). Ordering new vaccine for today."])`
WRONG output:   `FINISH(["No influenza vaccine found. Ordering new vaccine."])`

## Success Indicators

- Agent performs a second search using medication name text parameter after code search returns empty
- Agent finds vaccine records that were missed by code-only search
- Agent correctly extracts the date from the found record and applies the time threshold
- Agent only orders a new vaccine after confirming no recent administration exists

## Failure Indicators

- Agent stops after first empty code search and immediately orders a new vaccine
- Agent searches only MedicationRequest when the vaccine is stored as a Procedure
- Agent uses wrong search parameter (e.g., `medication` instead of `_text` on Procedure)
- Agent finds a record but fails to extract the date correctly, leading to incorrect time comparison
