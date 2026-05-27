---
description: Verify every active opioid order has a matching naloxone prescription
  and create missing naloxone orders.
name: opioid_naloxone_verification
provenance:
  action: ADD
  epoch: 0
  fixes: 8
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task8_26
  - task1_20
  - task8_23
  - task10_8
  - task8_29
  - task1_13
  - task3_10
  - task3_16
  - task2_14
  - task2_6
  update_cycle: 1
tags:
- opioid
- naloxone
- medicationrequest
- safety
version: 1
---

# Opioid‑Naloxone Verification

## Pattern Description
You must ensure that any **active opioid analgesic** MedicationRequest for a patient is accompanied by an **active naloxone** prescription. This pattern prevents patients from receiving opioids without a safety net. The skill works for any opioid medication (e.g., hydromorphone, oxycodone, fentanyl, hydrocodone, morphine) and any naloxone formulation (e.g., nasal spray, auto‑injector). It is triggered whenever a task asks to "verify opioid orders" or similar safety checks.

## When to Use This Skill
- When the instruction explicitly mentions *opioid analgesic* orders and a *naloxone* requirement.
- When a task asks to "verify every active opioid order has a matching naloxone prescription".
- When the agent receives a MedicationRequest bundle for a patient and must decide whether to create a naloxone order.

## Common Failure Patterns
- Querying only for naloxone and never checking for opioids, leading to a false "no opioid orders" conclusion.
- Looking for opioid **codes** in the `medicationReference` only, missing `medicationCodeableConcept` entries.
- Treating `status="completed"` as active; only `status="active"` (or `on-hold`) should be considered.
- Ignoring the `category` or `reasonCode` that may indicate the medication is an opioid.
- Failing to search the bundle for **both** opioid and naloxone resources before deciding.

## Recommended Patterns
**Pattern 1: Identify active opioid orders**
1. GET `MedicationRequest?patient={patientId}&status=active`.
2. For each entry, inspect:
   - `medicationCodeableConcept.coding.system` (e.g., RxNorm, SNOMED) and `code`.
   - Accept any of the opioid codes: `hydromorphone`, `oxycodone`, `fentanyl`, `hydrocodone`, `morphine` (include common RxNorm IDs).
3. Build a list `active_opioids` of MedicationRequest IDs.

**Pattern 2: Detect matching naloxone orders**
1. From the same bundle, filter entries where `medicationCodeableConcept.text` or `coding.display` contains "naloxone" (case‑insensitive) **and** `status=active`.
2. If `active_naloxone` is non‑empty, assume coverage for all opioids (clinical policy permits one naloxone per patient).

**Pattern 3: Create missing naloxone order**
1. If `active_opioids` is non‑empty **and** `active_naloxone` is empty:
   - POST a new `MedicationRequest` with:
     ```json
     {
       "resourceType": "MedicationRequest",
       "status": "active",
       "intent": "order",
       "medicationCodeableConcept": { "text": "NALOXONE NASAL SPRAY 4 MG" },
       "authoredOn": "{currentDateTime}",
       "dosageInstruction": [{ "route": { "text": "Intranasal" }, "doseAndRate": [{ "doseQuantity": { "value": 4, "unit": "mg" } }] }],
       "subject": { "reference": "Patient/{patientId}" }
     }
     ```
   - Use the same `authoredOn` as the current task timestamp.
2. Return a FINISH message summarising the action.

**Pattern 4: No action needed**
- If `active_opioids` is empty, FINISH with a statement that no opioid orders exist.
- If `active_opioids` is non‑empty **and** `active_naloxone` exists, FINISH confirming coverage.

## Example Application
**Task:** "Verify that every active opioid analgesic order for patient S1374652 has a matching naloxone prescription. If an opioid order is active without naloxone, create a naloxone order."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/MedicationRequest?patient=S1374652&status=active`.
2. Parse the bundle:
   - Find an entry with `medicationCodeableConcept.text` = "hydromorphone" → add to `active_opioids`.
   - No entry with "naloxone" → `active_naloxone` empty.
3. Because opioids are present and naloxone is missing, POST the naloxone MedicationRequest shown in Pattern 3.
4. FINISH: `FINISH(["Active opioid (hydromorphone) order found for patient S1374652. Naloxone nasal spray 4 mg order has been placed."])`

## Success Indicators
- The agent issues a POST for a naloxone MedicationRequest **only** when an active opioid is present and no active naloxone exists.
- The FINISH output explicitly mentions both the detection of opioid(s) and the creation (or confirmation) of naloxone.

## Failure Indicators
- FINISH states "no active opioid orders" when the GET bundle actually contains an active opioid entry.
- The agent creates a naloxone order even when an active naloxone already exists (duplicate orders).
- The agent never posts a naloxone order despite finding an active opioid and no naloxone.
- The POST payload omits required fields (`status`, `intent`, `medicationCodeableConcept`, `subject`).
