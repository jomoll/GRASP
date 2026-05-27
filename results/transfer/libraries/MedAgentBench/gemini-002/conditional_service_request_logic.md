---
description: Enforce strict output formatting for FINISH, suppressing sentinel values
  and narrative text.
name: conditional_service_request_logic
provenance:
  action: MODIFY
  epoch: 3
  fixes: 9
  parent_version: 2
  probe_score: 9
  regressions: 0
  triggering_sample_ids:
  - task10_27
  - task9_5
  - task2_25
  - task10_20
  - task10_16
  - task10_15
  - task9_8
  - task4_20
  - task5_3
  - task10_12
  update_cycle: 1
tags:
- formatting
- conditional-logic
- service-request
version: 3
---

# Conditional ServiceRequest Logic

## Pattern Description
When a task requires conditional logic (e.g., checking a lab result and potentially ordering a test), you must maintain a strict separation between the logic execution and the final output. The final output must be a clean, structured representation of the result, not a narrative summary or a mix of data and explanation.

## When to Use This Skill
- When a task requires checking a lab value and conditionally ordering a resource (e.g., ServiceRequest).
- When the task requires a specific output format (e.g., a list of values or a specific confirmation string).
- When you encounter a situation where no data is found (e.g., total=0 in a search bundle).

## Common Failure Patterns
- Including sentinel values (e.g., -1, "N/A") in the final `FINISH` output when the task expects a clean result or a specific confirmation.
- Returning verbose natural language explanations instead of the required structured data (e.g., `["5.4%", "2023-11-02"]`).
- Mixing POST confirmation messages with data extraction results in the same `FINISH` call.

## Recommended Patterns

**Pattern 1: Data Extraction**
If data is found, extract only the requested values into a list. Do not include units unless explicitly requested, and do not include conversational text.
CORRECT: `FINISH([5.4, "2023-11-02"])`
WRONG: `FINISH(["The value is 5.4% recorded on 2023-11-02"])`

**Pattern 2: Conditional Ordering**
If a condition triggers an order, perform the POST request first. Once the POST is confirmed, call `FINISH` with a concise confirmation string. Do not include the sentinel value (-1) or the logic explanation in the `FINISH` output.
CORRECT: `FINISH(["New HbA1C lab test ordered."])`
WRONG: `FINISH([-1, "Ordered new test"])`

**Pattern 3: No Data Found**
If no data is found and no order is required, return a clear, minimal indicator.
CORRECT: `FINISH(["No measurement available"])`

## Example Application

**Task:** "What’s the last HbA1C value and when was it recorded? If > 1 year old, order a new test."

**Step-by-step:**
1. GET the Observation.
2. If total=0, POST the ServiceRequest.
3. After POST success, call `FINISH(["No measurement available, new HbA1C lab test ordered."])`.

## Success Indicators
- `FINISH` output contains only the requested data or a clean confirmation message.
- No sentinel values (-1) appear in the final output.
- No conversational filler or logic explanation is included in the `FINISH` call.

## Failure Indicators
- `FINISH` output includes "-1", "N/A", or long-form sentences.
- The agent explains its reasoning inside the `FINISH` call.
