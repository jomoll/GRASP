---
description: Detect active opioid analgesic orders by matching MedicationRequest medication
  codes to a specified opioid list.
name: opioid_order_detection_by_medication_code
provenance:
  action: MODIFY
  epoch: 3
  fixes: 8
  parent_version: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task2_28
  - task3_16
  - task3_7
  - task2_17
  - task3_3
  - task8_23
  - task3_10
  - task3_29
  - task2_30
  - task2_6
  update_cycle: 1
tags:
- medication
- opioid
- order-detection
- naloxone
- fhir
version: 2
---

# Opioid Analgesic Order Detection by Medication Code

## Pattern Description

To reliably detect active opioid analgesic orders, you must inspect each active `MedicationRequest` for the patient and match the medication to a specified opioid list. This requires examining both the `medicationCodeableConcept` (including all `coding` entries and the `text` field) and, if present, the referenced `Medication` resource. Do not rely solely on the presence of a code or text string in the search parameters or summary lists—explicitly check each order's codes and display names for opioid matches.

This pattern is essential for tasks that require opioid stewardship, such as ensuring naloxone co-prescribing or auditing opioid use. False negatives occur if you miss opioid orders due to incomplete code matching or by failing to check all relevant fields.

## When to Use This Skill

- When verifying if a patient has any active opioid analgesic orders (e.g., hydromorphone, oxycodone, fentanyl, hydrocodone, morphine)
- When a task requires matching active MedicationRequest resources to a provided opioid list
- When the agent must decide whether to order naloxone or take other opioid-related actions

## Common Failure Patterns

- Only searching for opioids by name in the `medicationCodeableConcept.text` field, missing code-based matches
- Failing to check all `coding` entries within `medicationCodeableConcept.coding` (e.g., missing RxNorm or NDC codes)
- Ignoring referenced `Medication` resources when `MedicationRequest.medicationReference` is used
- Relying on search parameters like `&medication=naloxone` or `&code=naloxone` to filter opioids, which may not match all opioid orders
- Not normalizing or lowercasing text for comparison, leading to missed matches due to case or formatting differences

## Recommended Patterns

**Pattern 1: Comprehensive Code and Text Matching**
1. For each `MedicationRequest` with `status=active` for the patient, extract:
   - All codes in `medicationCodeableConcept.coding[]` (e.g., RxNorm, NDC, CPT)
   - The `medicationCodeableConcept.text` field
   - If `medicationReference` is present, resolve and extract codes/text from the referenced `Medication` resource
2. Compare each code and text value against the provided opioid list (by code and by normalized name).
   - Example opioid codes: RxNorm for hydromorphone, oxycodone, fentanyl, hydrocodone, morphine
   - Example opioid names: "hydromorphone", "oxycodone", etc. (case-insensitive)
3. If any match is found, treat as an active opioid order.

CORRECT: Detects opioid order if any code or text matches the opioid list
WRONG: Only detects if `medicationCodeableConcept.text` matches exactly

**Pattern 2: Fallback for Incomplete Coding**
- If no codes match but the `text` field contains an opioid name (case-insensitive, substring match), treat as a match.
- If the `MedicationRequest` uses a `medicationReference`, always resolve and check the referenced resource.

**Pattern 3: Output and Documentation**
- When reporting, explicitly list which opioid(s) were detected and by which field (code or text).
- If no opioid orders are found after comprehensive matching, state so clearly.

## Example Application

**Task:** "Verify that every active opioid analgesic order for patient S6550627 has a matching naloxone prescription."

**Step-by-step:**

1. GET all active MedicationRequests:
   - `GET /MedicationRequest?patient=S6550627&status=active`
2. For each entry:
   - Extract all codes from `medicationCodeableConcept.coding[]` and the `text` field
   - If `medicationReference` is present, GET the referenced Medication and extract codes/text
   - Compare all codes and text to the opioid list (e.g., RxNorm codes for hydromorphone, oxycodone, etc.)
3. If any match, proceed to check for naloxone; if none, report no active opioid orders
4. Example:
   - MedicationRequest: `{..., "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "197798", "display": "hydromorphone"}], "text": "HYDROMORPHONE (PF) 4 MG/ML INJ SOLN"}, ...}`
   - Opioid list includes RxNorm 197798 (hydromorphone)
   - CORRECT: Detects as opioid order
   - WRONG: Misses if only checking for "hydromorphone" in text

CORRECT output: `FINISH(["One active opioid analgesic order (hydromorphone) was found for patient S6550627.", ...])`
WRONG output:   `FINISH(["No active opioid analgesic orders found for patient S6550627."])`

## Success Indicators

- The agent detects all active opioid orders regardless of whether the match is by code or text
- The agent does not miss opioid orders due to code/text mismatch or incomplete field inspection
- The agent lists detected opioids and proceeds to check for naloxone as required

## Failure Indicators

- The agent reports no active opioid orders when one is present in the MedicationRequest (by code or text)
- The agent only checks the `text` field or only the code, missing matches in the other
- The agent fails to resolve and check referenced Medication resources
- The agent's output omits opioid orders that are present in the FHIR data
