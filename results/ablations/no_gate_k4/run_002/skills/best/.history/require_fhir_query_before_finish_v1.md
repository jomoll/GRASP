---
description: Enforce a GET request for any task that needs external FHIR data before
  issuing FINISH
name: require_fhir_query_before_finish
provenance:
  action: ADD
  epoch: 2
  no_gate: true
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task4_27
  - task5_19
  - task5_3
  - task4_20
  - task2_30
  - task4_4
  - task10_10
  - task4_15
  update_cycle: 1
tags: []
version: 1
---

# Require FHIR Query Before FINISH

## Pattern Description
You must never answer a clinical question that depends on patient data without first retrieving that data from the FHIR server.  Identify the resource type (Patient, Observation, Condition, etc.) from the task wording (e.g., *MRN*, *code*, *date range*), construct a correct GET request, wait for the response, and only then compute the answer and call `FINISH`.  This prevents the agent from fabricating values and guarantees that every answer is grounded in the current chart.

## When to Use This Skill
- When the instruction asks for a patient attribute such as age, gender, or identifiers (e.g., *"age of the patient with MRN S12345"*).
- When the instruction asks for the most recent lab value, vital sign, or any observation (e.g., *"most recent magnesium level"*, *"last serum potassium"*).
- When the instruction requires a conditional order based on a lab result (e.g., *"if potassium is low, order replacement"*).
- Any task that mentions a FHIR identifier (`MRN`, `code`, `date`) and expects a numeric or textual result.

## Common Failure Patterns
- The agent emits `FINISH` directly without any preceding `GET` request.
- The `GET` request is made to the wrong endpoint (e.g., `Patient` instead of `Observation`).
- Required query parameters are missing or malformed (`identifier=` missing, `code=` omitted, date range not expressed as `ge…`/`le…`).
- The agent extracts a value from a hard‑coded example instead of the response payload.

## Recommended Patterns
**Pattern 1: Identify and issue the correct GET**
1. Scan the task for a resource hint:
   - `MRN` → `Patient`
   - `code=` or a lab name → `Observation`
2. Build the URL:
   - Patient: `GET {base}/Patient?identifier={MRN}`
   - Observation: `GET {base}/Observation?code={LOINC|custom}&patient={MRN}&date=ge{START}&date=le{END}`
   - Include `_sort=-date&_count=1` when only the most recent entry is needed.
3. Issue the GET request **before** any other action.

**Pattern 2: Verify the response before proceeding**
- Confirm the response `Bundle.total` > 0.
- Extract the needed field (`birthDate`, `valueQuantity.value`, `effectiveDateTime`, etc.).
- If the bundle is empty, follow the task‑specific fallback (e.g., return `-1` or a no‑order message).

**Pattern 3: Finish only after processing**
- Perform any calculations (age, unit conversion, dosage) using the extracted data.
- Construct the `FINISH` payload exactly as the task specifies (numeric list, string list, or scalar string).
- Do **not** call `FINISH` until the GET response has been inspected.

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"

**Step‑by‑step:**
1. Detect a Patient lookup → `GET {base}/Patient?identifier=S2874099`.
2. Receive the Bundle, locate `entry[0].resource.birthDate`.
3. Compute age by subtracting the birth date from the provided current time, rounding down.
4. `FINISH([60])` (where `60` is the computed integer).

**Correct output:** `FINISH([60])`
**Wrong output:** `FINISH(60)` or `FINISH(["60"])` without a preceding GET.

## Success Indicators
- A `GET` request appears in the action log before any `FINISH`.
- The GET URL matches the expected pattern for the resource type.
- The `FINISH` payload contains a value derived from the GET response.

## Failure Indicators
- `FINISH` is emitted with no prior `GET`.
- The GET URL is malformed or points to the wrong resource.
- The answer contains hard‑coded or fabricated numbers.
- The output format does not match the task specification (e.g., wrong list type).
