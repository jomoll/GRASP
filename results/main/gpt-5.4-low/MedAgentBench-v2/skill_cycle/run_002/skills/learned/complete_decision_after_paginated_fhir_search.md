---
description: After paginated FHIR searches, synthesize the decision and FINISH instead
  of continuing to requery or abandoning.
name: complete_decision_after_paginated_fhir_search
provenance:
  action: ADD
  epoch: 1
  fixes: 2
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task1_20
  - task8_21
  - task8_19
  - task2_26
  - task3_16
  - task2_22
  - task3_27
  - task2_25
  - task3_29
  - task3_3
  update_cycle: 1
tags:
- pagination
- completion
- fhir-search
- decision-making
- observations
- medicationrequest
version: 1
---

# Skill Title

Complete Decision After Paginated FHIR Search

## Pattern Description

When a FHIR search returns a Bundle with `entry` data and possibly `link[relation="next"]`, you must treat pagination as a temporary data-gathering step, not the task itself. After you have enough records to answer the question, stop searching, apply the task-specific filter or calculation, and produce the required final action or `FINISH` response.

This matters most in tasks that ask you to verify coverage, count active orders, or compute a summary over a time window. A common failure is to keep following `_getpages` links, repeat similar searches, or abandon without comparing the gathered resources. Your behavior should change from "keep searching" to "search until enough, then decide and finish."

## When to Use This Skill

- When a GET on `Observation`, `MedicationRequest`, or `Procedure` returns a Bundle with `entry` and a `link` containing `relation: "next"`
- When the task asks for a computed result after retrieval, such as an average, latest date, active-order count, duplicate detection, or presence/absence check
- When you have already gathered candidate resources across one or more pages and the next step is comparison, filtering, counting, or calculation
- When you notice yourself issuing repeated `_getpages` requests without updating the assessment or moving toward a POST/FINISH
- When a broad search (for example `category=vital-signs` or all `MedicationRequest` for a patient) is being paged and the final answer depends on filtering the returned entries locally

## Common Failure Patterns

- Continuing to request `?_getpages=...&_getpagesoffset=...` after already having enough matching entries to answer the question
- Reissuing the original search instead of using the entries already collected from prior pages
- Failing to inspect `Bundle.entry[].resource.status`, `medicationCodeableConcept.text`, `code.coding`, or observation timestamps before deciding
- For time-window calculations, not splitting results by `effectiveDateTime`/`issued` into the requested windows before averaging
- For verification tasks, not comparing two subsets from the same retrieved list, such as opioid orders vs naloxone orders
- Returning no final answer after the last page, even though the Bundle data are sufficient to compute the result
- Posting an order before checking whether an existing matching active order is already present in the paged results

## Recommended Patterns

**Pattern 1: gather pages, then switch to local reasoning**
Issue the initial GET. If the Bundle has `entry`, collect the relevant `entry[].resource` items. If `link[relation="next"]` exists, follow it only as needed to gather candidate resources.

As you page, keep a working set of only relevant resources:
- `MedicationRequest`: inspect `status`, `intent`, `subject.reference`, `medicationCodeableConcept.text`, `medicationCodeableConcept.coding[]`
- `Observation`: inspect `code`, `category`, `valueQuantity.value`, `effectiveDateTime` or `issued`
- `Procedure`: inspect `code`, `performedDateTime` or `performedPeriod.start`

CORRECT: page through MedicationRequest results, then compare active opioid orders against active naloxone orders from the collected resources
WRONG: keep paging indefinitely without ever classifying which medications are opioids or naloxone

**Pattern 2: stop paging when the decision is already determined**
Do not assume every task requires every page. Stop once the result is logically determined.

Examples:
- Heart-rate average over past 12 hours: once you have all observations in the requested date-bounded query, compute the 6h and 12h subsets locally and finish
- DVT prophylaxis count: once all active prophylaxis candidates have been reviewed, decide zero/one/multiple and act
- Opioid/naloxone verification: once you know whether any active opioid lacks matching naloxone coverage, either POST naloxone or finish with no action

If the search was broad and paginated, but a later narrower date-bounded query returns a complete small set, use that smaller set and stop requerying.

**Pattern 3: always convert retrieved data into the requested final action**
After the last needed page, explicitly perform the task’s reasoning step:
1. Filter to matching resources.
2. Apply status/date/window rules.
3. Count, compare, or calculate.
4. If required, construct the POST body.
5. Call `FINISH` with the answer.

CORRECT: `FINISH([82.5, 79.2])` after averaging heart-rate values in the 6h and 12h windows
WRONG: `FINISH(["I reviewed several pages of observations."])`

For order-creation tasks:
- Verify absence/presence first from the collected resources
- Then POST exactly one needed order
- Then `FINISH` describing both the finding and the action

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S2161163."

**Step-by-step:**

1. Issue a date-bounded search such as:
   `GET /fhir/Observation?patient=<resolved-patient-id>&category=vital-signs&date=ge2023-11-07T10:47:00Z&date=le2023-11-07T22:47:00Z`
2. From `Bundle.entry[].resource`, keep observations whose code/text corresponds to heart rate and extract `valueQuantity.value`.
3. Read each observation timestamp from `effectiveDateTime` (or fallback `issued`).
4. Create two subsets:
   - past 6h: timestamps `>= 2023-11-07T16:47:00Z`
   - past 12h: timestamps `>= 2023-11-07T10:47:00Z`
5. Compute the numeric averages from the extracted `valueQuantity.value` values.
6. Return only the requested result format.

CORRECT output: `FINISH([84.0, 81.5])`
WRONG output: `FINISH(["I paged through observations but need more time."])`

**Task:** "Verify that every active opioid analgesic order has a matching naloxone prescription. If an opioid order is active without naloxone, create a naloxone order."

**Step-by-step:**

1. Issue:
   `GET /fhir/MedicationRequest?patient=<resolved-patient-id>`
2. If paginated, gather `entry[].resource` across needed pages.
3. Filter to active opioid orders using `status` plus medication text/coding, and separately filter active naloxone orders.
4. Compare the two sets. If any active opioid exists and no active naloxone is present, POST one naloxone order.
5. Immediately `FINISH` with the verification result and any action taken.

CORRECT output: `FINISH(["Active opioid order found without naloxone coverage.","Created naloxone nasal spray 4 mg order."])`
WRONG output: `GET /fhir?_getpages=...&_getpagesoffset=140...`

## Success Indicators

- After one or more paginated GETs, you stop and perform filtering/counting/calculation instead of issuing more exploratory searches
- You extract the exact resource fields needed for the task (`status`, `valueQuantity.value`, timestamps, medication text/codings)
- You either POST the required order/service request or call `FINISH` promptly after the decision is determined
- Your final answer reflects the requested computation or verification, not a summary of search activity

## Failure Indicators

- You continue `_getpages` requests after enough evidence is already present
- You repeat the original search with slightly different parameters instead of using collected entries
- You never form the requested subsets, such as 6h vs 12h windows or opioid vs naloxone lists
- You end the turn without `FINISH`, despite having paged through sufficient results
- You describe having reviewed records but omit the actual count, comparison, average, or required action
