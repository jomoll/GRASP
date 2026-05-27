---
description: Enforce specific, single-request FHIR queries to prevent redundant discovery
  and pagination errors.
name: efficient_fhir_query_strategy
provenance:
  action: ADD
  epoch: 3
  fixes: 2
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task10_24
  - task9_5
  - task10_21
  - task9_11
  - task10_20
  - task10_13
  - task10_17
  - task10_27
  update_cycle: 0
tags:
- fhir
- query-optimization
- efficiency
version: 1
---

## Skill Title
Efficient FHIR Query Strategy

## Pattern Description
When retrieving clinical data, you must avoid broad, iterative discovery queries. The FHIR server is most efficiently queried by combining specific search parameters (e.g., `patient`, `code`, `category`) into a single, targeted request. Avoid broad searches that return large bundles, as these trigger unnecessary pagination traversal and redundant follow-up queries.

## When to Use This Skill
- When you need to retrieve specific clinical data (e.g., lab results, observations) for a patient.
- When you have a specific identifier (MRN) and a specific code (e.g., LOINC code for a lab).
- When you are tempted to perform a broad search (e.g., `GET /Observation?patient=...`) to "discover" data.

## Common Failure Patterns
- Performing broad searches (e.g., `GET /Observation?patient=...`) that return large, irrelevant datasets.
- Attempting to traverse `_getpages` links, which often leads to 400 errors or task limit exhaustion.
- Issuing multiple redundant queries for the same resource after an initial search has already returned results.
- Querying by `category` alone when a specific `code` is available.

## Recommended Patterns

**Pattern 1: Targeted Retrieval**
Always combine the `patient` identifier with the specific `code` or `category` in the initial request. Use `_sort=-date` if you need the most recent record.

CORRECT: `GET /Observation?patient=S12345&code=2823-3&_sort=-date`
WRONG:   `GET /Observation?patient=S12345` followed by filtering in memory.

**Pattern 2: Avoid Pagination Traversal**
If a query returns a bundle, inspect the `entry` array directly. Do not attempt to follow `next` links unless the initial targeted query failed to return the required data.

**Pattern 3: Single-Pass Logic**
If the first targeted query returns `total: 0`, accept that the data is missing. Do not attempt to broaden the search (e.g., removing the `code` parameter) unless explicitly instructed to search for alternative codes.

## Example Application

**Task:** "Check patient S12345's most recent potassium level."

**Step-by-step:**
1. Identify the patient MRN (S12345) and the relevant code (2823-3).
2. Issue a single, targeted GET request: `GET /Observation?patient=S12345&code=2823-3&_sort=-date`.
3. Parse the `entry` array for the most recent observation.
4. If `total` is 0, conclude the data is unavailable and call `FINISH`.

## Success Indicators
- The agent retrieves the required data in 1–2 API calls.
- No 400 errors from invalid pagination attempts.
- No redundant queries for the same resource.

## Failure Indicators
- The agent performs more than 3 GET requests for a single data retrieval task.
- The agent attempts to follow `_getpages` links.
