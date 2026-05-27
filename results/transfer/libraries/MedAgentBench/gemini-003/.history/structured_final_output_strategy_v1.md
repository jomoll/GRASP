---
description: Enforce machine-readable list or tuple format for final answers to prevent
  conversational text.
name: structured_final_output_strategy
provenance:
  action: ADD
  epoch: 4
  fixes: 2
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_16
  - task10_27
  - task9_22
  - task5_19
  - task9_20
  - task10_13
  - task9_1
  - task9_8
  - task9_28
  - task5_7
  update_cycle: 1
tags:
- output-formatting
- structured-data
version: 1
---

# Structured Final Output Strategy

## Pattern Description
When a task requires returning specific data points (such as lab values, dates, or MRNs), you must provide the answer as a concise, machine-readable list or tuple. Avoid including natural language summaries, conversational filler, or explanatory sentences in the `FINISH` call. The goal is to provide only the requested data in the exact format specified by the task or the expected schema.

## When to Use This Skill
- When the task asks for specific data points (e.g., "What is the value and date?").
- When the agent has previously failed by returning a descriptive sentence instead of a structured list.
- When the expected output is a simple list of values, such as `[value, date]` or `[value]`.

## Common Failure Patterns
- Returning a full sentence: `FINISH(["The value is 5.4% recorded on 2023-11-02"])`.
- Including reasoning in the final output: `FINISH(["5.4%", "2023-11-02", "This is within range"]).`
- Mixing data types or adding unnecessary labels.

## Recommended Patterns

**Pattern 1: Data-Only Extraction**
Extract only the raw values requested. If the task asks for a value and a date, return them as a list of two elements.

CORRECT: `FINISH([5.4, "2023-11-02"])
WRONG:   `FINISH(["The value is 5.4%", "recorded on 2023-11-02"])

**Pattern 2: Handling Missing Data**
If the data is not found, return a specific indicator (like -1 or "Not found") as requested by the prompt, without conversational text.

CORRECT: `FINISH([-1])`
WRONG:   `FINISH(["I could not find the value, so I am returning -1"])

## Example Application

**Task:** "What’s the last HbA1C value and when was it recorded?"

**Step-by-step:**
1. Retrieve the observation using `fhir_observation_search_strategy`.
2. Extract the `valueQuantity.value` and `effectiveDateTime`.
3. Format the output as a list containing only these two elements.
4. Call `FINISH([5.4, "2023-11-02"])`.

## Success Indicators
- The `FINISH` call contains only the requested data points in a list format.
- No conversational text or explanatory sentences are present in the final output.

## Failure Indicators
- The `FINISH` call contains natural language sentences.
- The output includes reasoning or context that was not explicitly requested as part of the data structure.
