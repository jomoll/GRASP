---
description: Use LOINC codes and broad category searches for Observations when specific
  code searches fail, while ensuring exhaustive resource-specific searches for Procedures.
name: fhir_observation_search_strategy
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task3_7
  - task8_26
  - task3_14
  - task2_26
  - task9_9
  - task2_22
  - task6_13
  - task3_30
  - task3_3
  - task4_28
  update_cycle: 0
tags:
- fhir
- search-strategy
- observation
- procedure
version: 1
---

# FHIR Observation Search Strategy

## Pattern Description
When searching for clinical observations (vital signs, labs), relying solely on a single string-based code often leads to empty results. This strategy mandates a multi-tiered approach for Observations. For Procedures, ensure exhaustive searches across all relevant codes before concluding data is missing.

## When to Use This Skill
- When a search for a specific Observation code returns zero results.
- When the task requires clinical data (vitals, labs) and the initial specific search fails.
- When searching for Procedures (e.g., imaging, nursing interventions) and the initial code search returns zero.

## Recommended Patterns

**Pattern 1: Observation Multi-Tiered Search**
1. **Standardized Code:** Attempt search using recognized LOINC codes.
2. **Category Fallback:** If empty, search by `category` (e.g., `vital-signs`, `laboratory`) without the `code` filter. Inspect the bundle to identify the correct local codes.
3. **Verification:** Only conclude data is missing after both steps.

**Pattern 2: Procedure Exhaustive Search**
- Do not assume a procedure is missing based on a single code search. If a specific code search fails, perform a broader search (e.g., remove the `date` filter or search by a wider range) to ensure the procedure wasn't simply outside the initial time window before concluding it does not exist.

## Example Application

**Task:** "Calculate average heart rate for patient S2450227."
1. GET `.../Observation?patient=S2450227&code=8867-4`.
2. If empty, GET `.../Observation?patient=S2450227&category=vital-signs`.
3. Scan entries for heart rate data.

**Task:** "Check for recent CT Abdomen."
1. GET `.../Procedure?patient=S2450227&code=IMGCT0491,IMGIL0001`.
2. If empty, verify if the procedure exists at all (e.g., remove date constraints) before concluding it is missing.
