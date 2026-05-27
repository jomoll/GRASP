---
description: Always include a date filter when searching for procedures to find the
  most recent one, but only when the task explicitly mentions a time threshold or
  recency requirement
name: procedure_date_filter_required
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task8_26
  - task1_20
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task8_29
  - task1_13
  update_cycle: 1
tags: []
version: 1
---

# Procedure Date Filter Required

## Pattern Description

When a task requires finding the most recent procedure (e.g., CT Abdomen, urinary catheter placement, vaccination) **AND** the task explicitly mentions a time-based condition (e.g., "more than 12 months ago", "within the last 48 hours", "performed more than X days ago"), you must always include a `date` parameter in your FHIR Procedure search query. Without a date filter, the server may return results from any time period, but more critically, omitting the date filter can cause you to miss the most recent procedure or incorrectly conclude no procedure exists. The date filter ensures you retrieve only procedures within a relevant time window, allowing you to correctly identify the most recent one.

This skill applies to Procedure searches where the task involves determining recency, age, or time-based eligibility **and** the task provides a specific time threshold. The core lesson is: always compute a `date=ge` parameter based on the current time and the relevant lookback window, and include it in every Procedure GET request.

## When to Use This Skill

- When the task asks to "find the most recent" procedure of a specific type **AND** provides a time threshold (e.g., "more than 12 months ago", "within 48 hours")
- When the task requires checking if a procedure was performed more than a certain time ago (e.g., 12 months, 48 hours)
- When the task involves determining whether to order a new procedure based on the age of the most recent one **AND** specifies a time window
- When constructing a GET request to the Procedure endpoint and the task mentions a specific time threshold

## When NOT to Use This Skill

- When the task simply asks to "find the most recent" procedure without any time threshold (e.g., "Find the most recent TSH and free T4 values") — in these cases, omit the date filter to get all results and sort by date
- When the task involves retrieving lab values (Observation) rather than procedures — this skill is specific to Procedure searches
- When the task asks to review vaccination status without a specific time threshold (e.g., "Review COVID-19 vaccination status") — use a broader search without date filter first

## Common Failure Patterns

- Omitting the `date` parameter entirely from a Procedure search when the task has a time threshold, causing the server to return no results or incomplete results
- Using only `code` and `patient` parameters without a `date` filter when a time threshold is specified, then incorrectly concluding no procedure exists
- Using a date filter that is too narrow (e.g., only looking back 12 months when the procedure might be older) — but the primary failure is omitting the filter entirely when a time threshold is given
- Failing to compute the correct `date=ge` value from the current time and the task's time threshold

## Recommended Patterns

**Pattern 1: Always include a date filter in Procedure searches when a time threshold is specified**

1. Identify the current time from the task context (e.g., `Current time: 2023-11-07T22:47:00+00:00`).
2. Determine the lookback window from the task (e.g., "more than 12 months ago" means look back 12 months; "more than 48 hours" means look back 48 hours).
3. Compute the `date=ge` value: current time minus the lookback window. For 12 months, subtract 365 days; for 48 hours, subtract 2 days.
4. Include `date=ge<computed_date>` in the Procedure GET URL, along with `patient` and `code` parameters.

CORRECT: `GET /Procedure?patient=S2016972&date=ge2022-11-07&code=IMGCT0491,IMGIL0001`
WRONG:   `GET /Procedure?patient=S2016972&code=IMGCT0491,IMGIL0001` (no date filter)

**Pattern 2: When the task does NOT specify a time threshold, do NOT add a date filter**

1. Simply search with `patient` and `code` parameters.
2. Sort the results by date to find the most recent one.

CORRECT: `GET /Observation?patient=S1579803&code=TSH` (no date filter needed)
WRONG:   `GET /Observation?patient=S1579803&code=TSH&date=ge2022-11-07` (unnecessary date filter)

**Pattern 3: When the initial date-filtered search returns 0 results**

1. Do NOT immediately conclude no procedure exists. The procedure may be older than the lookback window.
2. Re-issue the search with a broader date range (e.g., go back further in time) to find any historical procedure.
3. If still no results after expanding the date range, then conclude no procedure exists.

**Pattern 4: Formatting the date parameter**

- Use the format `YYYY-MM-DD` for the date value (e.g., `date=ge2022-11-07`).
- URL-encode the date if it includes time components (e.g., `date=ge2023-11-09T09:00:00Z` becomes `date=ge2023-11-09T09%3A00%3A00Z`).
- For tasks with a threshold like "more than 12 months ago", compute the date as current date minus 365 days.

## Example Application

**Task:** "Find the date of the most recent CT Abdomen procedure for patient S2016972. If the study was performed more than 12 months ago, order a new CT Abdomen with IV contrast indication 'Renal mass follow-up'."

**Step-by-step:**

1. Current time from context: `2023-11-07T22:47:00+00:00`. The lookback window is 12 months (365 days).
2. Compute `date=ge`: `2023-11-07` minus 365 days = `2022-11-07`.
3. Issue GET: `GET /Procedure?patient=S2016972&date=ge2022-11-07&code=IMGCT0491,IMGIL0001`
4. Server returns 1 entry with `performedDateTime: "2023-06-14"`.
5. Compare `2023-06-14` to current time: it is less than 12 months ago (about 5 months).
6. Conclude: no new CT needed. Output: `FINISH(["The most recent CT Abdomen procedure for patient S2016972 was performed on 2023-06-14. Since this is less than 12 months ago, no new CT Abdomen is needed."])`

CORRECT output: `FINISH(["The most recent CT Abdomen procedure for patient S2016972 was performed on 2023-06-14. Since this is less than 12 months ago, no new CT Abdomen is needed."])`
WRONG output:   `FINISH(["No CT Abdomen procedures found for patient S2016972."])` (because date filter was omitted)

## Success Indicators

- Every Procedure GET request that has a time threshold includes a `date` parameter (e.g., `date=ge2022-11-07`)
- The agent correctly computes the date threshold from the current time and the task's time window
- The agent correctly interprets the results: if a procedure is found within the window, it uses its date for the recency check; if none found, it expands the search or concludes no procedure exists
- The agent does NOT add a date filter when the task simply asks to find the most recent item without a time threshold

## Failure Indicators

- A Procedure GET request is made without a `date` parameter when a time threshold is specified
- The agent incorrectly concludes no procedure exists because it omitted the date filter and got 0 results
- The agent uses the wrong date format (e.g., `date=2022-11-07` instead of `date=ge2022-11-07`)
- The agent fails to compute the correct lookback date (e.g., uses current date instead of current date minus threshold)
- The agent adds a date filter when no time threshold is specified, potentially missing results
