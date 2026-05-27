---
description: Detect active opioid analgesic orders by matching MedicationRequest medication
  codes to a specified opioid list.
name: opioid_order_detection_by_medication_code
provenance:
  action: ADD
  epoch: 1
  fixes: 3
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task2_30
  - task8_19
  - task9_22
  - task3_14
  - task2_22
  - task2_26
  - task2_1
  - task2_14
  - task3_7
  - task2_6
  update_cycle: 1
tags:
- medication
- opioid
- naloxone
- MedicationRequest
- code-matching
- stewardship
version: 1
---

# Opioid Order Detection by Medication Code

## Pattern Description

When verifying the presence of active opioid analgesic orders, you must not rely solely on the presence or absence of MedicationRequest resources for a patient. Instead, you must explicitly check whether any active MedicationRequest matches a known list of opioid analgesic medications, using their codes (e.g., RxNorm, NDC, or text display). This ensures that opioid orders are not missed or misclassified, and that downstream actions (such as naloxone prescribing) are only triggered when appropriate.

This pattern is essential for tasks that require opioid stewardship, such as ensuring every active opioid order has a matching naloxone prescription. It prevents false negatives that occur when the agent fails to filter MedicationRequests by the correct medication codes.

## When to Use This Skill

- When a task requires you to check for active opioid analgesic orders (e.g., hydromorphone, oxycodone, fentanyl, hydrocodone, morphine) for a patient.
- When the instruction specifies a list of opioid medications to search for, or when opioid stewardship is required.
- When you must determine if a naloxone prescription is needed based on the presence of opioid orders.

## Common Failure Patterns

- Reporting "no active opioid orders" after only checking for the presence of any MedicationRequest resources, without filtering by opioid codes.
- Failing to match opioid orders because only the text or display field is checked, not the coding system/code.
- Missing opioid orders that use synonyms or different display names but have the correct code.
- Using only the `medication=naloxone` parameter to check for naloxone, but not applying the same rigor to opioid detection.

## Recommended Patterns

**Pattern 1: Explicit Medication Code Matching**
1. Retrieve all active MedicationRequest resources for the patient (e.g., `GET /MedicationRequest?patient={id}&status=active`).
2. For each entry, inspect the `medicationCodeableConcept.coding` array:
   - Check if any coding entry's `system` and `code` match a known opioid analgesic (e.g., RxNorm codes for hydromorphone, oxycodone, fentanyl, hydrocodone, morphine).
   - If codes are not available, fall back to matching the `text` or `display` fields against the opioid list.
3. Only consider a MedicationRequest an "active opioid order" if it matches the opioid code list.

CORRECT: Identify an order for morphine by matching RxNorm code `7052` or NDC code, not just by display name.
WRONG: Assume any MedicationRequest is an opioid order if the display contains "pain" or if any order exists at all.

**Pattern 2: Fallback for Code Variants**
- If the opioid list includes multiple coding systems (RxNorm, NDC, etc.), check all relevant systems and codes.
- If the code is missing, use a case-insensitive substring match on `text` or `display` as a last resort, but only if codes are unavailable.

**Pattern 3: Downstream Decision**
- Only trigger naloxone prescription logic if at least one active MedicationRequest matches the opioid code list.
- If no such orders are found, report that no opioid order is present and no naloxone is needed.

## Example Application

**Task:** "Verify that every active opioid analgesic order for patient S1234567 has a matching naloxone prescription. If an opioid order is active without naloxone, create a naloxone order. Opioid medications to search for include hydromorphone, oxycodone, fentanyl, hydrocodone, morphine."

**Step-by-step:**

1. GET /MedicationRequest?patient=S1234567&status=active
2. For each entry, check if `medicationCodeableConcept.coding` contains a code for hydromorphone, oxycodone, fentanyl, hydrocodone, or morphine (e.g., RxNorm codes: hydromorphone 3423, oxycodone 7804, fentanyl 4337, hydrocodone 5489, morphine 7052).
3. If at least one match is found, proceed to check for naloxone orders.
4. If no match is found, FINISH(["No active opioid analgesic orders found for patient S1234567. No naloxone prescription is needed."])

CORRECT output: "No active opioid analgesic orders (hydromorphone, oxycodone, fentanyl, hydrocodone, morphine) found for patient S1234567. No naloxone prescription is needed."
WRONG output: "No active opioid analgesic orders found" (when there are active orders for morphine, but the agent did not check codes).

## Success Indicators

- The agent inspects each MedicationRequest's `medicationCodeableConcept.coding` for opioid codes.
- The agent only reports "no opioid orders" if none of the codes match the opioid list.
- Naloxone prescription logic is only triggered when an opioid order is positively identified by code.

## Failure Indicators

- The agent reports "no opioid orders" when active orders for opioids (by code) are present.
- The agent triggers naloxone logic for non-opioid orders or for any MedicationRequest without code filtering.
- The agent only checks for naloxone by code but not for opioids by code.
