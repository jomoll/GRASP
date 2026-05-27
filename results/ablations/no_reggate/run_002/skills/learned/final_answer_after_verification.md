---
description: Ensures the agent waits for and processes API responses before issuing
  FINISH, but exempts cases where a Patient GET is immediately followed by a request
  that uses the same patient reference (e.g., creating a ServiceRequest). This prevents
  premature FINISH while still allowing legitimate workflows that only need to confirm
  patient existence before another action.
name: final_answer_after_verification
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 12
  regressions: 1
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task4_11
  update_cycle: 0
tags: []
version: 1
---

# Final Answer After Verification (Refined)

## Goal
The agent must not call `FINISH` until any data required for the final answer has been extracted from a prior GET response **unless** the GET is a simple existence check for a Patient that is immediately used in a subsequent request (e.g., a POST/PUT/PATCH that references `Patient/{id}`).

## When to Apply
- **Apply** when a GET request is followed **directly** by `FINISH` (no other API calls in between).
- **Apply** when a GET request is the **last API call** before `FINISH` (i.e., no further GET/POST/PUT/PATCH after it).
- **Apply** for GETs of any resource type where the FINISH payload depends on values from that resource (e.g., extracting a lab value, medication dose, MRN, etc.).
- **Do NOT apply** when the GET is for a `Patient` and the **next** action is a request that includes a reference to that same patient (e.g., `POST ServiceRequest` with `subject.reference = "Patient/{identifier}"`). In this pattern the GET is only an existence check, and the subsequent request already encodes the needed reference.

## Core Verification Workflow (when the rule applies)
1. **Issue GET** with precise search parameters.
2. **Wait for the response** (the next turn will contain a `Bundle`).
3. **Parse the Bundle**:
   - Verify `total > 0` (resource exists).
   - Locate the first matching `entry.resource`.
   - Extract the exact field(s) required for the answer.
4. **Validate** the extracted value(s) (non‑empty, correct type, within expected range).
5. **Construct** the answer in the required format.
6. **Call FINISH** with the final answer.

## Exempted Pattern (Patient existence check)
1. `GET {api_base}/Patient?identifier={id}`
2. **Immediately** issue another request (POST/PUT/PATCH) that contains `reference: "Patient/{id}"`.
3. No need to parse the GET response before proceeding to the next request.
4. After the subsequent request completes, proceed to FINISH as usual.

## Fallback when no matching resource
- If `total == 0` or the required field is missing, produce the prescribed fallback (e.g., `"Patient not found"`, `-1`).
- Do **not** place orders or perform further actions until the fallback is confirmed.

## Formatting the final output
- Follow the task’s exact output spec (e.g., `FINISH([3.5])`, `FINISH(["Patient not found"])`).
- Do not embed explanatory text unless explicitly requested.

## Example – Non‑exempted (value extraction)
**Task:** "What’s the last HbA1C value for patient S6488980 and when was it recorded? If older than 1 year, order a new test."
1. `GET .../Patient?identifier=S6488980` → wait for Bundle.
2. `GET .../Observation?code=A1C&patient=S6488980` → wait for Bundle.
3. Parse Observation Bundle, extract the most recent `valueQuantity.value` and `effectiveDateTime`.
4. If the date is >1 year old, `POST` a new Observation request.
5. `FINISH([value, date])` (or appropriate fallback).

## Example – Exempted (Patient existence check)
**Task:** "Order orthopedic surgery referral for patient S2863714."
1. `GET .../Patient?identifier=S2863714`
2. **Immediately** `POST .../ServiceRequest` with `subject.reference = "Patient/S2863714"`.
3. No need to parse the GET response before the POST.
4. After POST succeeds, `FINISH(["Referral placed"])`.

## Success Indicators
- No `FINISH` appears immediately after a GET unless the GET is exempted as described.
- When the rule applies, the FINISH payload contains data extracted from the GET response (or the correct fallback).
- Exempted patterns proceed directly to the next request that references the patient.

## Failure Indicators
- `FINISH` follows a GET without an intervening response handling step **and** the GET is not an exempted Patient‑existence check.
- The final answer does not reflect data from the relevant GET response when required.
- Output type mismatches the specification.
