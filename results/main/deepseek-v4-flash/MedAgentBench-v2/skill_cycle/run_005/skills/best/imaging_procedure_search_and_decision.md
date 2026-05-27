---
description: Search Procedure resource for imaging studies and decide if new order
  needed
name: imaging_procedure_search_and_decision
provenance:
  action: ADD
  epoch: 1
  fixes: 1
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task1_11
  - task1_6
  - task3_7
  - task10_27
  - task1_20
  - task8_14
  - task2_14
  - task4_28
  - task9_6
  - task9_14
  update_cycle: 1
tags: []
version: 1
---

# Imaging Procedure Search and Decision

## Pattern Description

When a task asks you to find the most recent imaging study (CT, MRI, X-ray, etc.) for a patient and then decide whether to order a new one based on a time threshold, you must first search the Procedure resource without a date filter to find ALL matching procedures. Only after retrieving all results should you apply the time-based decision logic. Searching with a date filter first can cause you to miss older procedures that are still relevant to the decision.

This skill applies whenever you need to check if a prior imaging study exists and whether it was performed within a specific time window (e.g., 12 months, 48 hours, 365 days). The key insight is that you need the complete picture of all procedures before you can make an accurate time-based decision.

## When to Use This Skill

- When a task asks you to find the most recent imaging procedure (CT, MRI, ultrasound, X-ray) for a patient
- When the task specifies a time threshold (e.g., "more than 12 months ago", "within 48 hours", "in the last 365 days")
- When the task provides specific procedure codes (CPT, SNOMED, local codes) to search for
- When the task says "if no procedure found" or "if the study was performed more than X time ago"

## Common Failure Patterns

- Searching with `date=ge` filter first, which returns empty results when the only procedures are older than the filter date
- Concluding "no procedures found" when the real issue is that the date filter was too restrictive
- Ordering a new procedure without first confirming no prior procedure exists at all
- Using the current time to compute the date filter instead of using the task's reference date
- Not searching without any date parameter as a fallback when the date-filtered search returns zero results

## Recommended Patterns

**Pattern 1: Search without date filter first**
Before applying any time-based filter, issue a GET to the Procedure endpoint with only the patient ID and the procedure code(s). Do not include a `date` parameter in this initial search.

CORRECT: `GET /fhir/Procedure?patient=S1733937&code=IMGCT0491,IMGIL0001`
WRONG:   `GET /fhir/Procedure?patient=S1733937&date=ge2022-11-07&code=IMGCT0491,IMGIL0001`

**Pattern 2: Evaluate results against the time threshold**
Once you have all procedures, examine the `performedDateTime` or `performedPeriod` field of each entry. Sort by date descending to find the most recent. Compare the most recent date to the task's time threshold (e.g., 12 months ago from the current date or a reference date provided in the task).

- If the most recent procedure is within the threshold, report its date and do NOT order a new one.
- If the most recent procedure is older than the threshold, or if no procedures exist at all, then order a new procedure using the specified code and indication.

**Pattern 3: Ordering the new procedure**
When ordering a new imaging study, use the exact CPT code and indication provided in the task. Construct a ServiceRequest resource with the appropriate patient reference, code, and reasonCode.

## Example Application

**Task:** "Find the date of the most recent CT Abdomen procedure for patient S1733937. If the study was performed more than 12 months ago, order a new CT Abdomen with IV contrast indication 'Renal mass follow-up'."

**Step-by-step:**

1. Issue GET without date filter: `GET /fhir/Procedure?patient=S1733937&code=IMGCT0491,IMGIL0001`
2. Examine the response bundle. If `total` is 0, no prior procedure exists. Proceed to order a new one.
3. If procedures exist, find the one with the latest `performedDateTime`. Extract the date.
4. Compare to 12 months ago from the current date (or the reference date in the task context).
5. If the most recent procedure is more than 12 months old (or no procedure exists), create a ServiceRequest:
   - `status`: "active"
   - `intent`: "order"
   - `code`: CPT 74177
   - `reasonCode`: "Renal mass follow-up"
   - `subject`: reference to patient

CORRECT output when no procedure found: `FINISH(["No CT Abdomen procedures found for patient S1733937. Since no prior study exists, ordering a new CT Abdomen with IV contrast (CPT 74177) with indication 'Renal mass follow-up'."])`

WRONG output: `FINISH(["No CT Abdomen procedures found for patient S1733937 in the last 12 months. Ordering a new CT Abdomen with IV contrast (CPT 74177) with indication 'Renal mass follow-up'."])`

## Success Indicators

- The agent first searches Procedure without a date filter
- The agent correctly identifies the most recent procedure date from `performedDateTime`
- The agent correctly applies the time threshold comparison
- When no procedure exists, the agent orders a new one without claiming it was found "in the last 12 months"

## Failure Indicators

- The agent includes a `date=ge` parameter in the initial search
- The agent reports "no procedures found in the last X months" when the real issue is the date filter
- The agent orders a new procedure without checking if an older procedure exists
- The agent uses the wrong CPT code for the new order
