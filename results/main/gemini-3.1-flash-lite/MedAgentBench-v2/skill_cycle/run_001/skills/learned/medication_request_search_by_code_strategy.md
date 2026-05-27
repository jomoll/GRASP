---
description: Ensures medication searches use specific codes (RxNorm/LOINC) instead
  of relying on generic patient-wide requests.
name: medication_request_search_by_code_strategy
provenance:
  action: ADD
  epoch: 1
  fixes: 2
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task2_30
  - task8_19
  - task3_14
  - task2_22
  - task9_1
  - task2_26
  - task2_1
  - task2_14
  - task3_7
  - task2_6
  update_cycle: 1
tags:
- medication
- search
- fhir
version: 1
---

# Medication Request Search by Code Strategy

## Pattern Description
When searching for specific medication classes or types (e.g., opioids, vaccines), a generic `GET /MedicationRequest?patient=ID` often returns too many results, leading to pagination errors or missing specific orders. You must prioritize searching by specific codes (RxNorm, CPT, or LOINC) to narrow the scope and ensure accurate identification of active orders.

## When to Use This Skill
- When the task requires verifying the presence or absence of a specific medication or class (e.g., opioids, vaccines).
- When a broad `GET /MedicationRequest?patient=ID` returns a large bundle that is difficult to parse or triggers pagination errors.
- When you need to confirm if a specific order (like naloxone) exists to match an opioid order.

## Common Failure Patterns
- Relying on a broad `GET` request and failing to find the medication because it was buried in a large list.
- Assuming a lack of results from a broad search means the medication does not exist, without attempting a targeted search by code.
- Failing to handle pagination when a broad search returns many results.

## Recommended Patterns

**Pattern 1: Targeted Search**
Always attempt to search by the specific code provided in the task context first.
- Example: `GET /MedicationRequest?patient=S123&code=12345`

**Pattern 2: Fallback to Broad Search**
If the targeted search returns no results, perform a broader search but use `_count=100` to ensure you capture the full history.
- Example: `GET /MedicationRequest?patient=S123&_count=100`

**Pattern 3: Verification**
If you find no results after both targeted and broad searches, only then conclude that the medication is not present.

## Example Application

**Task:** "Verify that every active opioid analgesic order for patient S6530532 has a matching naloxone prescription."

**Step-by-step:**
1. Identify the relevant codes for opioids (e.g., hydromorphone, fentanyl).
2. Issue `GET /MedicationRequest?patient=S6530532&code=...` for each opioid.
3. If no results, issue `GET /MedicationRequest?patient=S6530532&_count=100` to confirm.
4. If still no results, conclude no naloxone is required.

## Success Indicators
- Agent performs targeted searches using `code` parameters.
- Agent successfully identifies medications that were previously missed in broad searches.

## Failure Indicators
- Agent continues to rely solely on broad `GET` requests without `code` parameters.
- Agent incorrectly concludes a medication is missing after a single, potentially incomplete, broad search.
