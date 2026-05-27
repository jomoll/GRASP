---
description: Use Bundle contents to decide no-result outcomes and never emit placeholder
  sentinels before parsing.
name: bundle_driven_no_result_handling
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task9_9
  - task10_27
  - task9_11
  - task10_15
  - task9_3
  - task10_21
  - task8_21
  - task10_16
  - task3_30
  - task10_12
  update_cycle: 0
tags:
- fhir
- bundle-parsing
- no-result-handling
- output-formatting
version: 1
---

# Skill Title

Bundle-Driven No-Result Handling

## Pattern Description

When I query FHIR and the task may legitimately have no matching data, I must base that conclusion on the returned Bundle payload, not on a placeholder value I invent before seeing the response. I should treat `Bundle.total`, `entry`, and the task's specified no-result format as the source of truth.

This skill changes two behaviors: first, I must never append `FINISH(...)` text or any placeholder output into a GET URL; second, I must never answer with a sentinel such as `-1`, `[]`, or `"Patient not found"` until I have inspected the actual response body. If the Bundle is empty, I then return the task-specific no-result answer. If the Bundle has entries, I must extract from those entries and continue the task logic.

## When to Use This Skill

- When issuing any `GET /Observation`, `GET /Patient`, or similar search where the task allows a no-result outcome
- When a task specifies a sentinel or fallback output such as `-1`, `[]`, or `"Patient not found"`
- When a prior run tendency is to send malformed URLs like `...?code=MGFINISH([-1])`
- When a `GET` response returns a FHIR `Bundle` with `total: 0` or no `entry`
- When reviewing chart data before deciding whether to place an order

## Common Failure Patterns

- Appending output text directly to the URL, e.g. `GET /Observation?patient=...&code=A1CFINISH([-1])`
- Returning `FINISH([-1])` before reading the `Bundle` for chart-review questions that require value/date or follow-up action
- Treating transport failure or malformed request as equivalent to confirmed no-result
- Ignoring `entry` when `Bundle.total > 0`
- Using the wrong no-result format for the task, e.g. returning `[-1]` when the task expects `[]` or a sentence
- Stopping after an empty lab search when the task still requires a narrative answer such as no prior result / no order placed

## Recommended Patterns

**Pattern 1: separate request construction from final answer**
Build the GET URL using only search parameters.

CORRECT: `GET /Observation?patient=S0658561&code=A1C`
WRONG:   `GET /Observation?patient=S0658561&code=A1CFINISH([-1])`

Do not draft placeholder `FINISH(...)` text in the same action as a GET. Wait for the response payload.

**Pattern 2: inspect the Bundle before deciding no-result**
After the GET returns, check in order:
1. `resourceType == "Bundle"`
2. `total`
3. `entry` presence and length
4. For each entry, `entry[i].resource`

If `total` is `0` or `entry` is absent/empty, only then produce the task-specific no-result output.
If entries exist, extract the needed fields and continue decision logic instead of using a sentinel.

**Pattern 3: map empty Bundle to the task's required output format**
Use the instruction to choose the no-result output:
- Numeric lookup task explicitly says use `-1` -> `FINISH([-1])`
- Action task says do nothing if no recent lab -> `FINISH([])` or the requested sentence
- Patient lookup says use `"Patient not found"` -> `FINISH(["Patient not found"])`
- Chart review asking for last result/date -> state no prior result in the final answer format, not `-1` unless explicitly requested

## Example Application

**Task:** "What’s the last HbA1C value in the chart for patient S0658561 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step-by-step:**

1. Issue GET with exact parameters:
   `GET /Observation?patient=S0658561&code=A1C`
2. Read the returned Bundle.
3. If `Bundle.total == 0` and there is no `entry`, conclude there is no prior HbA1C result in the chart.
4. Because there is no prior result, do not output `FINISH([-1])`. Instead, give the task-appropriate final answer stating no HbA1C result was found, and only place an order if the task/instructions imply ordering from absent data.

CORRECT output: `FINISH(["No HbA1C result found in the chart."])`
WRONG output:   `FINISH([-1])`

**Task:** "What’s the most recent magnesium level of the patient S6474456 within last 24 hours? The answer should be -1 if a measurement within last 24 hours is not available."

**Step-by-step:**

1. Issue GET exactly:
   `GET /Observation?patient=S6474456&code=MG&date=ge2023-11-12T10:15:00Z`
2. Inspect `Bundle.total` and `entry`.
3. If empty, return the specified sentinel because this task explicitly requests it.

CORRECT output: `FINISH([-1])`
WRONG output:   `GET /Observation?patient=S6474456&code=MG&date=ge2023-11-12T10:15:00ZFINISH([-1])`

## Success Indicators

- My GET URLs contain only valid path and query parameters
- I wait for the Bundle payload before deciding on no-result output
- Empty search results lead to the task-specific fallback format, not a generic placeholder
- Non-empty Bundles trigger extraction of value/date fields and any downstream order logic

## Failure Indicators

- `FINISH(...)` text appears inside a GET URL or query parameter value
- I return `-1`, `[]`, or `"Patient not found"` before seeing the response body
- I answer with a generic sentinel for a narrative chart-review task
- I ignore a non-empty `entry` array and still claim no result
- I treat a malformed request or 400 error as confirmed absence of data
