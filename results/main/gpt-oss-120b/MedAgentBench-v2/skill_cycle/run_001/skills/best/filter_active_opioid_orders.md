---
description: Filter MedicationRequest for active opioid analgesics and ensure a matching
  naloxone order exists. **Guard clause:** This skill only runs when the user instruction
  explicitly mentions an opioid analgesic (hydromorphone, oxycodone, fentanyl, hydrocodone,
  morphine, etc.) **and** a naloxone prescription. If those keywords are absent, the
  skill does nothing, preventing interference with unrelated tasks such as vaccine
  ordering.
name: filter_active_opioid_orders
provenance:
  action: ADD
  epoch: 3
  fixes: 3
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task3_7
  - task3_3
  - task4_21
  - task6_2
  - task8_23
  - task3_10
  - task2_30
  - task8_19
  - task2_1
  - task4_11
  update_cycle: 1
tags: []
version: 1
---

# Filter Active Opioid Orders and Verify Naloxone Coverage

## Guard Clause (Do Not Run on Irrelevant Tasks)
1. Examine the original user instruction (available as `{{instruction}}`).
2. If the instruction **does not contain** any of the opioid identifiers
   - `hydromorphone`
   - `oxycodone`
   - `fentanyl`
   - `hydrocodone`
   - `morphine`
   **or** does not contain the word `naloxone` (case‑insensitive),
   then **exit** the skill without performing any GET/POST actions and let other skills handle the request.

## Core Logic (Runs only when the guard clause passes)
### Pattern 1: Core filtering and naloxone verification
1. **GET** the MedicationRequest bundle for the patient.
2. Iterate over `bundle.entry` and keep entries where:
   - `resource.resourceType == "MedicationRequest"`
   - `resource.status` is one of `"active"`, `"on-hold"` (any status indicating the order is in effect).
   - `resource.medicationCodeableConcept` contains **any** of the opioid identifiers:
     - Text contains one of the opioid names above (case‑insensitive).
     - OR a coding with a known opioid RxNorm/ATC code (optional).
3. Collect the set of **active opioid MedicationRequest IDs**.
4. Separately, scan the same bundle for a **naloxone** order:
   - `resource.medicationCodeableConcept.text` contains `naloxone` (case‑insensitive) **or** a coding with a known naloxone code.
5. **If** the opioid set is non‑empty **and** no naloxone order is found, **POST** a new `MedicationRequest` for naloxone (use dosage, route, etc., supplied by the task).
6. **If** the opioid set is empty, finish with a statement that no opioid orders were found.

### Pattern 2: Fallback when bundle is empty or missing
- If the GET response has `total == 0` or no `entry` array, treat it as "no orders" and finish accordingly.
- If the response is malformed (missing `entry`), log a warning and fall back to a safe FINISH stating that the order list could not be retrieved.

### Pattern 3: Output formatting
- Always return a single‑element FINISH array with a concise, factual sentence.
- **Correct**: `FINISH(["No active opioid analgesic orders were found for patient S123; therefore no naloxone prescription is required."])`
- **Wrong**: `FINISH(["Patient has no opioids."])` (too vague) or embedding raw bundle data.

## Example Application
**Task:** "Verify that every active opioid analgesic order for patient S123456 has a matching naloxone prescription. If an opioid order is active without naloxone, create a naloxone order."

1. Guard clause passes because the instruction mentions `hydromorphone` (or any opioid) **and** `naloxone`.
2. `GET http://localhost:8080/fhir/MedicationRequest?patient=S123456`
3. Filter for active opioids as described.
4. If opioids exist and no naloxone entry is found, `POST` a naloxone `MedicationRequest`.
5. `FINISH(["All active opioid orders for patient S123456 have a matching naloxone prescription. A naloxone nasal spray 4 mg order was created."])

## Success Indicators
- The guard clause correctly detects opioid‑and‑naloxone‑related instructions.
- The agent extracts a non‑empty list of active opioid MedicationRequest IDs when appropriate.
- The agent checks for an existing naloxone order before creating a new one.
- The FINISH output explicitly mentions the presence or absence of opioid orders and the action taken.

## Failure Indicators
- The skill runs on a task that does **not** mention opioids or naloxone (e.g., vaccine ordering) and produces unrelated MedicationRequest actions.
- The agent finishes with a generic statement without inspecting the bundle.
- The agent creates a naloxone order even when a naloxone entry already exists.
- The FINISH output is vague or omits whether a naloxone order was created.

---
*This revised proposal adds a strict guard clause to ensure the skill only activates for opioid‑naloxone scenarios, preventing regressions on unrelated tasks such as influenza vaccine ordering.*
