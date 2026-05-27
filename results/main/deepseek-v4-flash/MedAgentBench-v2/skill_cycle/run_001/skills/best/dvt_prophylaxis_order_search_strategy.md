---
description: Search for DVT prophylaxis orders by medication name, not just category
name: dvt_prophylaxis_order_search_strategy
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - task1_23
  - task10_27
  - task1_6
  - task10_15
  - task9_11
  - task1_15
  - task3_14
  - task4_11
  - task9_14
  - task3_7
  update_cycle: 0
tags: []
version: 1
---

# DVT Prophylaxis Order Search Strategy

## Pattern Description

When verifying or managing DVT prophylaxis orders, you must search for the specific medications by generic name or RxNorm code, not just by the `category=Inpatient` parameter. The `category` parameter alone is unreliable because DVT prophylaxis orders may be stored under different categories (e.g., `Community`, `Outpatient`, or no category at all) depending on the system configuration. The correct approach is to search for the specific medication names (e.g., `heparin`, `enoxaparin`, `dalteparin`, `fondaparinux`) using the `medication` search parameter on `MedicationRequest`.

This skill teaches you to always include a medication-specific search when the task involves a known drug or drug class, rather than relying solely on category-based filtering. The core lesson is: when you know the exact medication or medication class, search for it directly.

## When to Use This Skill

- When the task asks you to verify, find, or manage DVT prophylaxis orders (e.g., heparin, enoxaparin, LMWH)
- When you receive a `GET /MedicationRequest?patient=X&category=Inpatient` response with `total: 0` but the task expects an existing order
- When constructing a search for any medication where you know the generic name or therapeutic class
- When the task context explicitly names a medication (e.g., "heparin 5000 units SC q8h prophylaxis")

## Common Failure Patterns

- Searching only by `category=Inpatient` and concluding no orders exist when orders are actually present under a different category
- Searching only by `category=Inpatient` and missing orders that have no category or a different category value
- Failing to search by medication name (`medication=heparin` or `medication.code=...`) when the medication is known
- Using `category=inpatient` (lowercase) which may not match the server's expected value `Inpatient` (case-sensitive)
- Not combining medication name search with `status=active` to filter for active orders only

## Recommended Patterns

**Pattern 1: Primary search by medication name**
When the task specifies a known DVT prophylaxis medication (e.g., heparin, enoxaparin), search using the `medication` parameter with the generic name. Use the RxNorm code if known.

CORRECT: `GET /MedicationRequest?patient=S6307599&medication=heparin&status=active`
WRONG:   `GET /MedicationRequest?patient=S6307599&category=Inpatient`

**Pattern 2: Broaden search if first attempt returns empty**
If the medication-specific search returns zero results, broaden the search to include all DVT prophylaxis medications. Search for each known medication separately or use a combined approach.

CORRECT: `GET /MedicationRequest?patient=S6307599&medication=enoxaparin&status=active` (then try heparin, dalteparin, etc.)
WRONG:   Concluding "no orders found" after only one search attempt

**Pattern 3: Verify active status**
After retrieving orders, check the `status` field of each `MedicationRequest` entry. Only consider orders with `status=active` as current. Filter out `stopped`, `cancelled`, `completed`, or `entered-in-error` orders.

CORRECT: Check `entry[i].resource.status === "active"`
WRONG:   Counting all returned orders regardless of status

## Example Application

**Task:** "Verify that patient S6307599 has exactly one active DVT prophylaxis order. If there are zero orders, create one. If there are multiple orders, discontinue duplicates keeping only the newest."

**Step-by-step:**

1. Search for heparin orders specifically:
   `GET http://localhost:8080/fhir/MedicationRequest?patient=S6307599&medication=heparin&status=active`

2. If the response bundle has `total: 0`, search for other DVT prophylaxis medications:
   `GET http://localhost:8080/fhir/MedicationRequest?patient=S6307599&medication=enoxaparin&status=active`
   `GET http://localhost:8080/fhir/MedicationRequest?patient=S6307599&medication=dalteparin&status=active`

3. If any search returns results, examine the `entry` array. For each entry, check `resource.status` is `"active"` and `resource.medicationCodeableConcept.text` or `coding` matches a DVT prophylaxis drug.

4. Count the active orders. If count == 1, no action needed. If count == 0, create a new order. If count > 1, discontinue all but the newest (by `authoredOn` date).

CORRECT output: `FINISH(["Patient S6307599 has 1 active heparin order. No action needed."])`
WRONG output:   `FINISH(["No active DVT prophylaxis orders found for patient S6307599."])` (when orders exist but were missed)

## Success Indicators

- Agent searches by medication name (e.g., `medication=heparin`) instead of or in addition to `category=Inpatient`
- Agent finds existing DVT prophylaxis orders that were previously missed
- Agent correctly identifies zero, one, or multiple active orders
- Agent creates a new order only when truly zero active orders exist

## Failure Indicators

- Agent still searches only by `category=Inpatient` and concludes no orders exist
- Agent searches by medication name but uses wrong parameter name (e.g., `code` instead of `medication`)
- Agent finds orders but fails to check `status=active`, counting inactive orders
- Agent creates a duplicate order when an active order already exists but was missed
