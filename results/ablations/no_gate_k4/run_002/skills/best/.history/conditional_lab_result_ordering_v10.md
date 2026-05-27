---
description: Skip ordering when the required lab result is missing or already recent
  enough
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 9
  triggering_sample_ids:
  - task4_27
  - task9_9
  - task5_16
  - task9_27
  - task2_26
  - task5_19
  - task2_16
  - task10_24
  - task9_14
  - task10_21
  update_cycle: 0
tags: []
version: 10
---

# Conditional Lab Result Ordering

## Pattern Description
You must decide whether to create a ServiceRequest based on **both** the numeric value **and** the existence/recency of the lab result. If the result is absent, or if the most recent value is within the acceptable time window, the agent must **not** place an order. This prevents unnecessary orders that were previously triggered by placeholder values like "-1".

## When to Use This Skill
- Tasks that request the latest lab value **and** specify a follow‑up order if the value is older than a threshold (e.g., >1 year for HbA1c, low magnesium within 24 h).
- The preceding lab query skill has supplied either a valid value/date **or** a null result.
- The agent is about to construct a `POST /ServiceRequest`.

## Common Failure Patterns
- Ordering a new HbA1c test when the original query returned no result (placeholder "-1").
- Ordering replacement magnesium when the query returned no observation.
- Ignoring the `lab_date` recency check and ordering regardless of how recent the existing result is.

## Recommended Patterns
**Pattern 1: Validate existence before threshold check**
1. After the lab query, ensure `lab_value` and `lab_date` are not null.
2. If either is null, set `order_needed = false` and record a message like "No result found – no order placed".

**Pattern 2: Apply the time‑based threshold only on existing results**
1. Compute `age = now - lab_date`.
2. If `age > threshold` **and** `lab_value` is present, set `order_needed = true`.
3. Otherwise, `order_needed = false`.

**Pattern 3: Build the ServiceRequest only when needed**
- When `order_needed` is true, POST the ServiceRequest with the appropriate LOINC/SNOMED code.
- When false, skip the POST and include a clear note in the FINISH output.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6550627 and when was it recorded? If the result is >1 year old, order a new test."

**Step‑by‑step:**
1. Perform the Observation GET (returns `total: 0`).
2. Lab query skill sets `lab_value = null`, `lab_date = null`.
3. Conditional ordering logic:
   - Detect null → `order_needed = false`.
   - Prepare FINISH: `FINISH(["No HbA1c result found", "No order placed"])`.
4. No POST is issued.

**Correct output:** `FINISH(["No HbA1c result found", "No order placed"])`
**Wrong output:** `FINISH(["-1", "HbA1C test ordered"])`

## Success Indicators
- No ServiceRequest POST is made when the lab result is missing or recent enough.
- FINISH includes an explicit "No order placed" note when appropriate.
- The agent logs a decision path showing the null‑check before ordering.

## Failure Indicators
- A POST is still executed despite `lab_value` being null.
- The FINISH output contains an order message without a valid lab value.
- The agent reports an order but the ServiceRequest cannot be retrieved (as seen in system notes).
