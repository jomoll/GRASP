---
description: Check latest lab recency and place a new ServiceRequest when the result
  is older than the task threshold.
name: lab_recency_check_with_reorder
provenance:
  action: ADD
  epoch: 1
  fixes: 12
  probe_score: 11
  regressions: 0
  triggering_sample_ids:
  - task4_4
  - task9_28
  - task4_23
  - task5_19
  - task9_8
  - task10_16
  - task4_28
  - task4_7
  - task10_12
  - task10_15
  update_cycle: 0
tags:
- labs
- observation
- servicerequest
- recency
- reorder
version: 1
---

# Lab Recency Check With Reorder

## Pattern Description

When a task asks for the latest lab result and also gives a freshness rule such as "if older than 1 year, order a new test," you must treat this as a two-step workflow: retrieve the most recent historical result, then make a recency decision before finishing. The reusable lesson is that finding a value is not the end of the task when the prompt includes an age threshold tied to a reorder action.

This should change behavior in result-review tasks so you do not stop after returning an old result or an empty result set. Instead, you must inspect the result timestamp, compare it to the task's reference time, and submit a new `ServiceRequest` if the latest available result is too old or if no qualifying result exists and the task implies a new test is needed.

## When to Use This Skill

- When the task asks for the last/most recent lab value and also says to order a new test if the result date is older than a stated threshold
- When a `GET /Observation?code=...&patient=...` returns results, but the task includes wording like "if greater than 1 year old"
- When a `GET /Observation?code=...&patient=...` returns `total: 0` or empty `entry`, and the task is a monitoring/reorder workflow rather than a pure lookup
- When ordering a follow-up lab requires a different code system/value than the Observation search code (example: search `code=A1C`, order LOINC `4548-4`)

## Common Failure Patterns

- Calling `FINISH([-1])` immediately after `GET /Observation?code=A1C&patient=...` returns `total: 0`, without placing the requested new lab order
- Returning the last historical value/date but not comparing `effectiveDateTime` to the task's current time and threshold
- Using the wrong date field for recency; ignoring `effectiveDateTime` and relying on unrelated metadata
- Forgetting that the order code may differ from the lookup code, such as searching A1C observations with `code=A1C` but ordering HbA1C using LOINC `4548-4`
- Posting a `ServiceRequest` without a valid patient reference in `subject.reference`
- Finishing with only value/date when the task required both reporting the old result and ordering a new test

## Recommended Patterns

**Pattern 1: retrieve latest result, then evaluate recency**
First, resolve the patient if needed with `GET /Patient?identifier=...`. Then query observations with the exact search code from the task, for example `GET /Observation?code=A1C&patient=S6545016`.

From returned observations, identify the latest result by the clinical result time, preferring `effectiveDateTime`. Extract the result value from `valueQuantity.value` when present, or the task-appropriate value field. Compare the latest result timestamp to the task's current time and threshold.

CORRECT: extract latest `effectiveDateTime` and compare to 1-year cutoff
WRONG: return the first bundle entry without checking date or stop after finding any result

**Pattern 2: if stale or absent, place a new lab order**
If the latest result is older than the threshold, or if no relevant observation exists and the task says to order a new test in that case, create a `ServiceRequest`.

Use the ordering code specified by the task, not necessarily the search code. For HbA1C reorder tasks, use:
- `resourceType: "ServiceRequest"`
- `status: "active"`
- `intent: "order"`
- `subject.reference: "Patient/<patient_id>"`
- `authoredOn: <current time from task>`
- `code.coding[0].system: "http://loinc.org"`
- `code.coding[0].code: "4548-4"`
- `code.coding[0].display: "Hemoglobin A1c/Hemoglobin.total in Blood"` if display is needed

**Pattern 3: complete the answer with both review and action**
After ordering, finish with the requested result payload format, including the last known value/date when available, plus a concise statement that a new order was placed if the task expects narrative confirmation. If there was no prior result, say so and state that a new order was placed.

CORRECT: report old A1C value/date and note reorder when stale
WRONG: `FINISH([-1])` after no observation results in a reorder-required task

## Example Application

**Task:** "What’s the last HbA1C value in the chart for patient S6545016 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

## Step-by-step:

1. Issue `GET /Patient?identifier=S6545016` and confirm the patient exists.
2. Issue `GET /Observation?code=A1C&patient=S6545016`.
3. Find the most recent observation by `effectiveDateTime`. Suppose the latest is `2023-07-07T11:27:00+00:00` with `valueQuantity.value = 5.7`.
4. Compare to current time `2023-11-13T10:15:00+00:00`. This is less than 1 year old, so do not order.
5. Return the latest value/date only.

CORRECT output: `FINISH([5.7,"2023-07-07T11:27:00+00:00"])`
WRONG output: `FINISH(["5.7%","2023-07-07T11:27:00+00:00","No action needed"])`

**Task:** "What’s the last HbA1C value in the chart for patient S2016972 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

## Step-by-step:

1. Issue `GET /Patient?identifier=S2016972`.
2. Issue `GET /Observation?code=A1C&patient=S2016972`.
3. If the response has `total: 0`, do not stop at no result.
4. Create `POST /ServiceRequest` with body like:
   `{"resourceType":"ServiceRequest","status":"active","intent":"order","subject":{"reference":"Patient/S2016972"},"authoredOn":"2023-11-13T10:15:00+00:00","code":{"coding":[{"system":"http://loinc.org","code":"4548-4","display":"Hemoglobin A1c/Hemoglobin.total in Blood"}]}}`
5. Finish by indicating no prior result was found and a new HbA1C was ordered, in the task's expected output style.

CORRECT output: `FINISH(["No prior HbA1C result found","HbA1C lab ordered"])`
WRONG output: `FINISH([-1])`

## Success Indicators

- You always compare the latest lab timestamp to the task's freshness threshold before finishing.
- When the result is stale, your actions include a `POST /ServiceRequest` before `FINISH`.
- When no result exists in a reorder-required lab task, you order the lab instead of returning `-1`.
- The `ServiceRequest.subject.reference` uses the resolved patient ID correctly.
- The order code matches the task-specified ordering code, even if it differs from the observation search code.

## Failure Indicators

- You return an old lab value/date but never place the required order.
- You end with `FINISH([-1])` or similar no-result output after an empty Observation search in a reorder-required task.
- You skip the date comparison entirely.
- You build the `ServiceRequest` with the search code (`A1C`) instead of the specified order code (`4548-4`).
- You post an order missing `subject.reference`, `status`, `intent`, or `authoredOn`.
- Your final output omits the action taken when the task required both review and reorder.
