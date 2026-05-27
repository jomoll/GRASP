---
description: Add explicit opioid code filtering and active status check to ensure
  naloxone is ordered when needed
name: opioid_naloxone_verification
provenance:
  action: MODIFY
  epoch: 2
  fixes: 6
  parent_version: 1
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task2_1
  - task3_3
  - task8_26
  - task3_7
  - task2_14
  - task3_27
  - task1_20
  - task2_30
  - task1_13
  - task2_26
  update_cycle: 1
tags:
- opioid
- naloxone
- medicationrequest
- verification
version: 2
---

# Opioid Naloxone Verification

## Pattern Description
You must verify that every **active** opioid analgesic order for a patient has a matching naloxone prescription. The pattern is reusable for any opioid‑based pain regimen: first locate opioid orders using a predefined list of medication codes, confirm they are active, then search for a naloxone order with the same patient reference. If an active opioid order lacks a naloxone counterpart, create a naloxone MedicationRequest.

## When to Use This Skill
- When a task asks to "verify every active opioid analgesic order has a matching naloxone prescription".
- When the patient identifier is known and a `MedicationRequest?patient=...` query is performed.
- When the instruction includes a list of opioid medication names or codes (e.g., hydromorphone, oxycodone, fentanyl, hydrocodone, morphine).

## Common Failure Patterns
- **Missing code filter** – the skill queries all MedicationRequests and treats the bundle as if it only contains opioids.
- **Ignoring `status`** – orders with `status` = `completed` or `entered-in-error` are counted as active.
- **Incorrect naloxone code** – searching for a generic "naloxone" text instead of the exact CPT/RxNorm code.
- **Assuming empty bundle means no opioids** – a bundle may contain non‑opioid meds; the skill must explicitly check each entry.

## Recommended Patterns
**Pattern 1: Identify active opioid orders**
1. Issue `GET /MedicationRequest?patient={patientId}`.
2. For each entry in the returned Bundle:
   - Inspect `medicationCodeableConcept.coding[].code` (or `medicationReference`).
   - **Match** against the opioid code list (e.g.,
     ```
     opioid_codes = [
       "860975",   # hydromorphone (RxNorm)
       "860976",   # oxycodone
       "860977",   # fentanyl
       "860978",   # hydrocodone
       "860979"    # morphine
     ]
     ```
   - Verify `status` is `active` (or `draft`/`on-hold` that are still in effect).
   - Collect the `id` of each matching order.

**Pattern 2: Verify matching naloxone order**
1. Issue a second `GET /MedicationRequest?patient={patientId}` (reuse the same bundle if already fetched).
2. Look for entries where `medicationCodeableConcept.coding[].code` equals the naloxone code (e.g., RxNorm `860980` or CPT `NDC12345`).
3. If **no** naloxone entry is found **and** the opioid list from Pattern 1 is non‑empty, proceed to Pattern 3.

**Pattern 3: Create missing naloxone order**
```json
POST /MedicationRequest
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medicationCodeableConcept": {
    "coding": [{
      "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
      "code": "860980",
      "display": "Naloxone"
    }]
  },
  "subject": { "reference": "Patient/{patientId}" },
  "authoredOn": "{today_iso}"
}
```

**Pattern 4: Reporting**
- If opioid list is empty → `FINISH(["No active opioid analgesic orders found for patient {patientId}; no naloxone prescription needed."])`.
- If naloxone already present → `FINISH(["Active opioid orders have matching naloxone; no new order required."])`.
- If naloxone created → `FINISH(["Naloxone order created for patient {patientId} to accompany active opioid(s)."])`.

## Example Application
**Task:** Verify that every active opioid analgesic order for patient S1796597 has a matching naloxone prescription.

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/MedicationRequest?patient=S1796597`.
2. Iterate entries; find two active opioids with codes `860975` and `860978` → record their IDs.
3. Scan the same bundle for a naloxone entry (`code == "860980").` None found.
4. `POST` the naloxone MedicationRequest shown in Pattern 3.
5. `FINISH(["Naloxone order created for patient S1796597 to accompany active opioid(s)."])`.

**Correct output:**
```
FINISH(["Naloxone order created for patient S1796597 to accompany active opioid(s)."])
```
**Wrong output (previous behavior):**
```
FINISH(["No active opioid analgesic orders found for patient S1796597; no naloxone order needed."])
```

## Success Indicators
- The agent extracts and filters `medicationCodeableConcept.coding[].code` against the opioid list.
- The agent checks `status` == `active` before deciding an opioid is “active”.
- When needed, the agent issues a `POST` with the exact naloxone RxNorm/CPT code.
- The final FINISH message accurately reflects whether a naloxone order was created or not.

## Failure Indicators
- The agent reports "no active opioid orders" while the bundle contains opioid entries.
- The agent creates a naloxone order even when a matching naloxone entry already exists.
- The agent posts a naloxone request with an incorrect code or missing required fields (`status`, `intent`, `subject`).
- The FINISH message does not mention naloxone creation when it should.
