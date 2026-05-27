---
description: After a successful order-creating POST, immediately FINISH with the decision
  summary instead of continuing to browse.
name: post_then_immediate_finish_for_order_tasks
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - task8_26
  - task1_20
  - task9_5
  - task8_23
  - task8_29
  - task1_13
  - task3_10
  - task3_16
  - task2_14
  - task1_16
  update_cycle: 1
tags:
- completion
- post
- finish
- orders
- medicationrequest
- servicerequest
version: 1
---

# Skill Title

## Post-Then-Finish Completion Pattern

## Pattern Description

When a task asks you to assess data and create an order only if needed, the task is not complete when the POST succeeds. You must still submit the answer. After you have gathered enough evidence, made the decision, and successfully created the requested order, you should stop searching and immediately call `FINISH(...)` with a concise summary of the assessment and the action taken.

This pattern is especially important in chart-review workflows that involve long paginated searches or fallback queries. Once the requested order has been created, additional browsing usually adds no value and can cause task-limit failures. Your behavior should change from "keep investigating" to "close the loop with a final answer" as soon as the POST is accepted.

## When to Use This Skill

- When a task says to review history, decide whether an order is needed, and create it if indicated
- When a `POST /fhir/MedicationRequest` or `POST /fhir/ServiceRequest` succeeds and the user says the request was accepted
- When the user message after POST says `Please call FINISH if you have got answers for all the questions and finished all the requested tasks`
- When you already know the key facts needed for the final answer, such as the last vaccine date, presence/absence of naloxone, or whether zero existing prophylaxis orders were found
- When you reached the decision point after paginated `MedicationRequest` or `Procedure` review and the requested order has already been placed

## Common Failure Patterns

- Posting the order and then taking no further action, causing `answer_never_submitted_after_order`
- Posting the order and continuing pagination with `_getpages` or more broad searches instead of finishing
- Treating successful POST acceptance as the final step without a `FINISH(...)` call
- Returning to re-query the just-created order even though the task only requires assessment plus order placement
- Finishing without including the assessment basis, e.g. saying only `Order placed` instead of also stating the last vaccine date or the opioid/naloxone gap
- Omitting whether an order was created or not from the final answer

## Recommended Patterns

**Pattern 1: core strategy or rule**
After each successful POST, immediately ask yourself: "Do I already have the facts needed to answer the task?" If yes, call `FINISH(...)` in the very next step.

Include both:
1. the decision basis from the review
2. the action taken

CORRECT: `FINISH(["Last COVID vaccine date: 2021-10-10.", "Because this was more than 12 months ago, a COVID booster was ordered today."])`
WRONG: continuing with `GET http://localhost:8080/fhir?_getpages=...`

**Pattern 2: fallback or verification rule**
Do not require post-POST verification retrieval unless the task explicitly asks you to verify storage. A user message saying the POST was accepted is sufficient to proceed to `FINISH(...)`.

If the task involved pagination, rely on the evidence you already extracted before posting. Do not resume `_getpages` navigation after order creation unless a required question remains unanswered.

**Pattern 3: formatting or completion rule**
Your final `FINISH(...)` should summarize the completed workflow in 1-4 short strings.

Include task-specific facts such as:
- opioid/naloxone review: active opioid found or not, naloxone missing or present, order created or not
- vaccine review: most recent vaccine date or none found, threshold comparison, booster ordered or not
- prophylaxis review: count of active qualifying orders, whether a new order was created

CORRECT: `FINISH(["Reviewed active opioid orders for patient S1374652.", "Found active hydromorphone order without naloxone coverage.", "Created naloxone order: NALOXONE NASAL SPRAY 4 MG."])`
WRONG: `FINISH(["Done"])`

## Example Application

**Task:** "Review COVID-19 vaccination status for patient S6551923. Find the most recent COVID-19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step-by-step:**

1. Issue review queries such as `GET /fhir/Procedure?patient=S6551923&code=COVIDVACCINE...` and any needed `MedicationRequest` history queries.
2. Extract the most recent vaccine date from the history, or determine that none is documented.
3. Compare that date to the task threshold of 12 months and decide a booster is needed.
4. Create the order with `POST /fhir/MedicationRequest` or `POST /fhir/ServiceRequest`.
5. As soon as the user confirms the POST was accepted, immediately submit the final answer.

CORRECT output: `FINISH(["Most recent documented COVID-19 vaccine date: 2021-10-10.", "Because the last dose was more than 12 months ago, a COVID booster order was placed today."])`
WRONG output: continue querying `GET /fhir?_getpages=...` after the accepted POST, or say nothing.

## Success Indicators

- After a successful order-creating POST, your very next action is `FINISH(...)`
- The final answer includes both the review conclusion and the action taken
- You stop paginating or issuing exploratory GETs once the requested order has been accepted
- The task completes within the action limit even for long medication-history reviews

## Failure Indicators

- A successful POST is followed by silence or more unnecessary GET requests
- The transcript ends after the user says the POST was accepted, without `FINISH(...)`
- You create the correct order but never provide the requested final answer
- The final answer lacks the key factual basis for the order decision
- You keep searching after POST even though all requested questions were already answered
