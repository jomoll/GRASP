---
description: Ensures medication searches include both generic and brand names to prevent
  false negatives.
name: comprehensive_medication_search_strategy
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - task3_10
  - task4_10
  - task3_30
  - task4_6
  - task4_27
  - task8_29
  - task3_16
  - task6_26
  - task3_29
  - task8_23
  update_cycle: 0
tags:
- medication
- search
- fhir
version: 1
---

# Comprehensive Medication Search Strategy

## Pattern Description
When searching for medications, the FHIR server may only index specific names or codes. Relying on a single search term often leads to false negatives where active orders are missed because they are recorded under a different synonym, brand name, or generic equivalent.

## When to Use This Skill
- When a task requires verifying the presence or absence of a specific medication (e.g., opioids, anticoagulants, vaccines).
- When an initial search for a medication returns zero results, but the task context implies the medication might be present under a different name.

## Common Failure Patterns
- Searching only by a single generic name (e.g., "hydromorphone") and missing brand-name equivalents (e.g., "Dilaudid").
- Assuming a zero-result search means the medication is not present, without checking for related classes or synonyms.

## Recommended Patterns

**Pattern 1: Broaden Search Terms**
If the initial search for a specific medication returns no results, perform a secondary search using a broader set of synonyms or the drug class if applicable.

**Pattern 2: Verify with Patient-Level Search**
If specific code searches fail, perform a broader search for all `MedicationRequest` resources for the patient and filter the results manually in your reasoning process.

**Example Application**

**Task:** "Verify that every active opioid analgesic order for patient S6500497 has a matching naloxone prescription."

**Step-by-step:**
1. Perform initial search: `GET /MedicationRequest?patient=S6500497`.
2. If no results are found, do not immediately conclude the patient has no opioids.
3. Inspect the bundle for any medication that matches the opioid class (hydromorphone, oxycodone, fentanyl, hydrocodone, morphine).
4. If the bundle is large, use the `_count` parameter to ensure you are not missing records due to pagination.

## Success Indicators
- Agent identifies active orders that were previously missed by narrow searches.
- Agent correctly identifies the absence of a medication only after a comprehensive search of the patient's medication history.

## Failure Indicators
- Agent reports "no orders found" after a single, narrow search query.
- Agent fails to account for brand/generic name variations.
