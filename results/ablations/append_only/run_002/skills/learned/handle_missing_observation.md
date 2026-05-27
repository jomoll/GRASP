---
description: Detect empty Observation bundles and apply a fallback query or report
  no result
name: handle_missing_observation
provenance:
  action: ADD
  epoch: 0
  fixes: 8
  probe_score: 6
  regressions: 4
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task1_20
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  update_cycle: 1
tags:
- observation
- fallback
- missing_data
version: 1
---

# Missing Observation Handling with Fallback

## Pattern Description
You must robustly handle cases where a FHIR `Observation` search returns no entries. Instead of immediately returning a placeholder value, first verify the bundle, then optionally broaden the search window before concluding that the observation truly does not exist. This prevents premature answers and gives the agent a chance to find older data that may still satisfy the clinical question.

## When to Use This Skill
- When you issue a `GET /Observation` with a specific `code`, `patient`, and a time filter (e.g., `date=ge2023-11-12T10:15:00Z`) and the task expects a numeric result or a sentinel value like `-1` if no recent measurement exists.
- When the returned Bundle has `"total": 0` (i.e., no matching Observation resources).
- When the task description mentions a fallback strategy (e.g., "if not available, return -1") or when the clinical logic depends on the presence of a recent value.

## Common Failure Patterns
- Ignoring the `total` field and returning `-1` (or any placeholder) without confirming that the bundle is empty.
- Failing to attempt a broader date range before concluding that no observation exists.
- Returning a placeholder value in the wrong format (e.g., as a string array `"[-1]"` instead of the expected JSON array `[-1]`).

## Recommended Patterns
**Pattern 1: Verify bundle content**
1. After the `GET /Observation` call, parse the JSON response.
2. Inspect `bundle.total` (or count of `bundle.entry`).
3. If `total > 0`, proceed with normal extraction (e.g., `valueQuantity.value`).
4. If `total == 0`, continue to Pattern 2.

**Pattern 2: Fallback date range**
1. Construct a second GET request expanding the time window (e.g., `date=ge2023-11-05T10:15:00Z` for a 7‑day look‑back).
2. Repeat the bundle verification steps.
3. If the fallback also returns `total == 0`, you have confirmed the observation is truly missing.

**Pattern 3: Return a verified placeholder**
1. When both primary and fallback queries yield no results, finish with the sentinel value **exactly** as required by the task (e.g., `FINISH([-1])`).
2. Optionally include a short explanatory note in the output if the task permits (e.g., `FINISH([-1, "No recent magnesium level found"])`).

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S2937751 within last 24 hours? Return -1 if no measurement is available."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S2937751&date=ge2023-11-12T10:15:00Z`
2. Parse response – `"total": 0` → no recent magnesium.
3. Fallback: `GET http://localhost:8080/fhir/Observation?code=MG&patient=S2937751&date=ge2023-11-05T10:15:00Z`
4. Parse fallback – still `"total": 0`.
5. `FINISH([-1])` (exact JSON array, no extra strings).

**Correct output:** `FINISH([-1])`
**Wrong output:** `FINISH(["-1"])` or returning `-1` without the verification steps.

## Success Indicators
- The agent checks `bundle.total` after each Observation query.
- A fallback query is issued when the first query returns no entries.
- The final `FINISH` call contains the sentinel value in the exact format required by the task.

## Failure Indicators
- The agent returns `-1` (or any placeholder) immediately after the first GET, without inspecting `total`.
- No fallback query is attempted despite an empty primary result.
- The placeholder is wrapped in a string or extra text, violating the expected output schema.
