---
description: "Order replacement medication when a recent lab value is below a defined\
  \ low\u2011threshold."
name: lab_threshold_ordering
provenance:
  action: ADD
  epoch: 2
  fixes: 11
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - task5_3
  - task4_4
  - task10_10
  - task3_16
  - task10_13
  - task9_20
  - task3_19
  - task10_18
  - task9_22
  update_cycle: 1
tags: []
version: 1
---

# Lab Threshold Ordering

## Pattern Description
You must automatically decide whether to place a replacement medication order based on the most recent laboratory result for a given analyte. The skill extracts the numeric value (and its units) from the latest Observation, compares it to a clinically‑defined low‑threshold, and, if the value is below that threshold, creates a `ServiceRequest` for the appropriate replacement drug and optionally schedules a follow‑up lab. This pattern applies to any lab‑driven replacement scenario (e.g., low potassium → potassium chloride, low magnesium → IV magnesium).

## When to Use This Skill
- When the task asks to *"check the most recent <lab> level and if low, order replacement"*.
- When the task provides a lab code (e.g., `K` for potassium, `MG` for magnesium) and a replacement medication NDC or dosing instruction.
- When a 24‑hour window is specified for the lab retrieval.

## Common Failure Patterns
- Extracting the lab value as a string (e.g., `"4.0 mmol/L"`) instead of a numeric type, causing comparison errors.
- Ignoring the unit and comparing raw strings, leading to false negatives.
- Failing to compare the value against the low‑threshold, resulting in no order being placed.
- Placing an order even when the lab value is normal or when the user did not request an order.

## Recommended Patterns
**Pattern 1: Retrieve and extract the latest lab value**
1. GET `Patient?identifier=<MRN>` to obtain the patient reference.
2. GET `Observation?code=<LAB_CODE>&patient=<patient_ref>&date=ge<now-24h>` to fetch recent observations.
3. From the returned bundle, select the entry with the most recent `effectiveDateTime`.
4. Extract `valueQuantity.value` as a number and `valueQuantity.unit` as a string.
5. Convert the unit to the expected standard if necessary (e.g., `mmol/L` → keep as is for potassium, `mg/dL` for magnesium).

**Pattern 2: Compare against low‑threshold and decide**
- Define low‑thresholds (example values):
  - Potassium: `3.5 mmol/L`
  - Magnesium: `1.5 mg/dL`
- If `extracted_value < low_threshold` **AND** the task explicitly mentions ordering when low, proceed to Pattern 3.
- If the value is ≥ threshold, do **not** create an order.

**Pattern 3: Create replacement order**
1. Build a `ServiceRequest` with:
   - `status: "active"`
   - `intent: "order"`
   - `code.coding` set to the replacement medication (use provided NDC or known SNOMED code).
   - `subject.reference` set to the patient reference.
   - `authoredOn` set to the current timestamp.
   - `priority` as appropriate (`stat` for urgent, `routine` otherwise).
   - Optional `note.text` describing the low result and dosing instructions.
2. POST the `ServiceRequest` to `/ServiceRequest`.
3. If a follow‑up lab is required (e.g., repeat potassium next morning), also POST a `ServiceRequest` for the lab with `occurrenceDateTime` set to the desired time.

## Example Application
**Task:** "Check patient S0636132's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Patient?identifier=S0636132` → obtain `Patient/S0636132`.
2. GET `http://localhost:8080/fhir/Observation?code=MG&patient=Patient/S0636132&date=ge2023-11-12T10:15:00`.
3. Choose the most recent entry; suppose `valueQuantity.value = 1.2` and `unit = "mg/dL"`.
4. Compare: `1.2 < 1.5` → low.
5. POST `ServiceRequest` with magnesium replacement coding, subject `Patient/S0636132`, note "Magnesium 1.2 mg/dL < 1.5 mg/dL – order IV magnesium replacement."
6. FINISH([]).

**CORRECT output:** a successful POST and `FINISH([])`.
**WRONG output:** returning only the lab value without ordering, or ordering when the value is ≥ threshold.

## Success Indicators
- The agent posts a `ServiceRequest` for the replacement medication **only** when the extracted lab value is below the defined low‑threshold.
- The posted `ServiceRequest` contains the correct patient reference, medication code, and a note mentioning the low value.
- If a follow‑up lab is required, a second `ServiceRequest` for the lab is also posted with the correct `occurrenceDateTime`.

## Failure Indicators
- The agent finishes without posting any order despite the lab value being below threshold.
- The agent posts an order when the lab value is normal or when the task never asked for an order.
- The posted `ServiceRequest` lacks the patient reference or uses the MRN string instead of `Patient/<id>`.
- The numeric comparison fails because the value was treated as a string (e.g., "1.2" vs 1.5).
