---
description: Use _sort=-date and multiple code aliases when searching for laboratory
  observations to ensure the most recent data is retrieved.
name: fhir_observation_search_strategy
provenance:
  action: ADD
  epoch: 3
  fixes: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task5_3
  - task9_11
  - task9_27
  - task10_12
  - task10_8
  - task10_16
  - task10_21
  - task10_17
  - task9_20
  - task9_9
  update_cycle: 0
tags:
- fhir
- search
- observation
- lab-results
version: 1
---

## Skill Title
FHIR Observation Search Strategy

## Pattern Description
When searching for laboratory observations, the agent must ensure it retrieves the most recent data and accounts for potential variations in coding (e.g., LOINC codes vs. local display names). Relying on a single, potentially incomplete search query often leads to missing records or empty results. This skill mandates using sorting parameters and, if necessary, iterative searching to ensure the chart is accurately represented.

## When to Use This Skill
- When searching for a specific lab result (e.g., HbA1C, Potassium, Magnesium) and the initial search returns no results or an empty bundle.
- When the task requires the "most recent" value, necessitating a chronological sort.

## Common Failure Patterns
- Searching without `_sort=-date`, which may return older records or require manual filtering of large bundles.
- Assuming a single code (e.g., 'A1C') is sufficient when the system might index the record under a different code or display text.
- Concluding a value is missing after only one search attempt without trying alternative identifiers or sorting.

## Recommended Patterns

**Pattern 1: Sort by Date**
Always append `&_sort=-date` to your `GET /Observation` requests to ensure the most recent entry appears first in the bundle.

**Pattern 2: Multi-Code Search**
If a search for a specific code (e.g., `code=A1C`) returns zero results, immediately attempt a secondary search using the formal LOINC code (e.g., `code=4548-4`) or other known aliases before concluding the data is missing.

**Pattern 3: Verification**
If the search returns a bundle, inspect the `entry` array. If the array is empty, do not immediately assume the value is missing; verify if the `total` count is 0 or if the search parameters were too restrictive.

## Example Application

**Task:** "What is the last HbA1C value for patient S6550627?"

**Step-by-step:**
1. Perform initial search: `GET /Observation?patient=S6550627&code=A1C&_sort=-date`
2. If `total` is 0, perform secondary search: `GET /Observation?patient=S6550627&code=4548-4&_sort=-date`
3. If both return 0, only then conclude the value is unavailable.
4. If a result is found, extract the `valueQuantity.value` from the first entry in the sorted bundle.

## Success Indicators
- The agent successfully retrieves the most recent observation by using `_sort=-date`.
- The agent finds records that were previously missed by trying alternative codes.

## Failure Indicators
- The agent reports "not found" despite the record existing under a different code or being buried in a large, unsorted list.
