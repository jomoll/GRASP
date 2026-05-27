---
description: Select the most recent microbiology observation when the query asks for
  the last or latest test.
name: microbiology_observation_latest_selection
provenance:
  baseline_fixes: 3
  baseline_regressions: 5
  epoch: 14
  failure_mode: wrong_specimen_selected
  fixes: 7
  probe_score: 7
  regressions: 2
  triggering_sample_ids:
  - 01bb1845215fb7cc77678534
  - 031f4556ea1fe707a94f58bb
  - 0cf19476dc727db127ab20bf
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill after `microbiology_observation_filter` when the user question contains keywords such as **last**, **most recent**, **latest**, or **first time since** and the answer requires a single timestamp or observation.

## Procedure
1. Receive the list of filtered microbiology observations produced by `microbiology_observation_filter`.
2. Extract each Observation’s effective datetime:
   - Prefer `effectiveDateTime`.
   - If missing, use `effectivePeriod.start`.
3. If the question includes a date range (e.g., *since 03/2115*), discard observations with datetime earlier than the start date.
4. Sort the remaining observations by their effective datetime.
5. **Selection rule**:
   - If the question asks for the **last / most recent** test, pick the observation with the **maximum** datetime.
   - If the question asks for the **first** test (e.g., *first csf test*), pick the observation with the **minimum** datetime.
6. Return the selected Observation (or just its datetime/value as required by the downstream answer logic).

## Checks
- Ensure at least one observation remains after filtering; if none, answer “No matching test found”.
- Confirm that the datetime objects are timezone‑naïve or normalized to UTC before comparison.
- Verify that the selected observation still satisfies any additional constraints (e.g., specific organism presence) that may be handled by downstream code.

## Avoid
- Returning the earliest observation when the user explicitly asked for the last one.
- Ignoring the date‑range filter supplied in the question.
- Selecting an observation without a valid datetime.
