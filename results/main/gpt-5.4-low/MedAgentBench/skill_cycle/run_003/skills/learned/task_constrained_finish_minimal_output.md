---
description: Do not emit FINISH until all required API responses are parsed and the
  exact final answer shape is known.
name: task_constrained_finish_minimal_output
provenance:
  action: MODIFY
  epoch: 3
  fixes: 2
  parent_version: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task10_24
  - task10_13
  - task10_15
  - task8_13
  - task9_28
  - task9_3
  update_cycle: 1
tags:
- finalization
- answer-format
- workflow-control
version: 2
---

# Task-Constrained Finalization After Evidence Is Complete

## Pattern Description

You must treat `FINISH(...)` as the last step, not as a placeholder while waiting for data. Before answering, complete the needed GET/POST actions, read the returned Bundle or success message, and determine the exact answer schema required by the task. This skill applies whenever the task expects a tightly constrained array output and the temptation is to narrate uncertainty or emit a provisional answer.

A common failure is to produce an early `FINISH(["Unable to complete..."])` before the Observation or Patient response has actually been parsed, or to accidentally append `FINISH(...)` text onto a GET URL. The correct behavior is to keep querying, parse the actual response, then emit one final task-shaped answer only after all required work is done.

## When to Use This Skill

- When a task requires `FINISH([...])` in a specific arity or schema and I have not yet parsed the latest GET response
- When I have issued a GET `/Observation`, `/Patient`, or similar search but the user has not yet provided the Bundle contents
- When I am about to write explanatory text such as "Unable to complete", "Patient not found", or "ordered X" before checking `Bundle.total` or `entry`
- When a task combines retrieval plus conditional ordering, and the final answer depends on both parsed results and whether a POST was actually sent
- When the interface says "Please call FINISH if you have got answers for all the questions and finished all the requested tasks"

## Common Failure Patterns

- Emitting `FINISH(["Unable to complete without the Observation query response bundle."])` before the Bundle arrives
- Appending `FINISH(...)` text directly to a request URL, such as `GET /Patient?identifier=S0636132FINISH([])`
- Returning explanatory narration when the task expects only raw values, such as `[5.8,"2022-09-09T15:33:00+00:00","ordered HbA1C lab"]` when the schema only allows value/date
- Calling `FINISH` after only the first subtask is done in a multi-step instruction
- Using guessed no-result strings before inspecting `Bundle.total`, `entry`, or the POST success message

## Recommended Patterns

**Pattern 1: never finalize before parsing evidence**
Before answering, wait until the user has supplied the response for every GET/POST that matters to the task. Parse the returned JSON first.

CORRECT: issue `GET /Observation?...`, read `Bundle.entry`, extract value/date, then decide whether to POST or FINISH
WRONG: issue `GET /Observation?...` and immediately output `FINISH(["Unable to complete..."])`

If the task has multiple required steps, keep working until all are complete. `FINISH` must appear only once, after the final decision.

**Pattern 2: keep tool calls and final answers strictly separate**
A GET or POST line must contain only the request. Never include `FINISH(...)`, comments, or narrative in the same line or URL.

CORRECT: `GET http://localhost:8080/fhir/Patient?identifier=S6545016`
WRONG:   `GET http://localhost:8080/fhir/Patient?identifier=S6545016FINISH(["Patient not found"])`

If I am uncertain, I should issue the next needed request or wait for its response—not draft a placeholder final answer.

**Pattern 3: map the parsed result to the task's exact output schema**
After parsing the evidence and completing any required POST, produce only the fields the task asked for, in the right order and arity.

Examples:
- Retrieval task expecting one number: `FINISH([2.0])`
- No-action clinical decision task expecting empty output: `FINISH([])`
- A1C retrieval task expecting value and timestamp only: `FINISH([5.8,"2022-09-09T15:33:00+00:00"])`

Do not add status narration unless the task explicitly asks for it.

## Example Application

**Task:** "What’s the last HbA1C value in the chart for patient S6521727 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step-by-step:**

1. Issue `GET /Observation?patient=S6521727&code=A1C`.
2. Wait for the Bundle response; do not call `FINISH` yet.
3. Parse the most recent Observation and extract `valueQuantity.value` and the result date field used by the task logic.
4. Compare the parsed date to the current time. If older than 1 year, issue `GET /Patient?identifier=S6521727`, parse the Patient Bundle, then POST the `ServiceRequest`.
5. After required actions are complete, return only the requested answer shape.

CORRECT output: `FINISH([5.8,"2022-09-09T15:33:00+00:00"])`
WRONG output:   `FINISH(["Unable to complete without the Observation query response bundle."])`
WRONG output:   `FINISH([5.8,"2022-09-09T15:33:00+00:00","ordered HbA1C lab"])`

## Success Indicators

- I do not emit any `FINISH` before the relevant GET/POST responses are available and parsed
- Request URLs are clean and contain no embedded final-answer text
- The final output appears exactly once and matches the task's required array schema
- Multi-step tasks complete retrieval and conditional ordering before finalization

## Failure Indicators

- Any provisional or apologetic `FINISH(...)` appears before a response Bundle is parsed
- A GET or POST request string contains `FINISH`, narration, or extra text not belonging to the URL/body
- The final answer includes extra explanatory strings or wrong number of array elements
- I finalize before completing a required POST or before confirming that no action is needed
