---
description: Require a verified Patient GET before any Observation query and enforce
  correct patient reference format.
name: observation_patient_precondition
provenance:
  action: ADD
  epoch: 3
  fixes: 4
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task9_5
  - task9_11
  - task4_4
  - task10_13
  - task8_13
  - task9_22
  - task5_3
  - task9_27
  update_cycle: 0
tags:
- observation
- patient_resolution
- precondition
version: 1
---

# Observation Patient Precondition

## Pattern Description
You must always resolve the patient resource before querying any Observation that is scoped to a specific patient. This guarantees that the patient exists, that you have the correct MRN, and that the Observation request uses the proper FHIR reference format (`Patient/{MRN}`). The pattern applies to any task that mentions a lab code (e.g., potassium, magnesium, A1C) together with a patient identifier.

## When to Use This Skill
- The task description contains a laboratory or vital‑sign code (e.g., "potassium", "magnesium", "HbA1C", "BP") **and** a patient identifier such as "patient S123456" or "MRN S123456".
- The agent is about to issue a `GET /Observation` request that includes a `patient=` query parameter.
- No successful `GET /Patient` request for the same MRN has been recorded earlier in the execution trace.
- The `patient=` value does **not** start with the required `Patient/` prefix.

## Guard Clause
- If the task does **not** mention a patient identifier or a lab/vital code, ignore this skill.
- If a `GET /Patient?identifier={MRN}` has already succeeded (Bundle `total >= 1` and an entry with `resource.id` matching `{MRN}`), the skill allows the Observation request to proceed.
- If the Observation request already uses the correct `patient=Patient/{MRN}` format **and** the patient has been resolved, the skill does nothing.

## Common Failure Patterns
- Observation query issued before any Patient GET.
- Observation query uses `patient=S123456` (missing `Patient/` prefix).
- Observation query repeats after a failed patient lookup, leading to 400 errors.
- Observation query uses an incorrect MRN (typo) because the MRN was never extracted from a verified Patient resource.

## Recommended Patterns
**Pattern 1: Resolve patient first**
1. Extract the MRN string from the task (e.g., `S123456`).
2. Issue `GET {api_base}/Patient?identifier={MRN}`.
3. Verify the response is a `Bundle` with `total >= 1` and that the first entry's `resource.id` equals `{MRN}`.
4. Store the canonical reference `Patient/{MRN}` for later use.

**Pattern 2: Validate Observation request**
1. Before any `GET /Observation` that includes a `patient=` parameter, check that a patient reference has been stored.
2. If the request uses `patient={MRN}` without the `Patient/` prefix, rewrite the URL to `patient=Patient/{MRN}`.
3. If no patient has been resolved yet, insert the Patient GET from Pattern 1 before the Observation request.

**Pattern 3: Fallback on failure**
- If the Patient GET returns `total == 0`, abort the task with `FINISH(["Patient not found"])`.
- If the Observation request still fails after correction, log the error and abort with a clear message.

## Example Application
**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium."

**Step‑by‑step:**
1. Detect MRN `S6474456` and code `K` in the description.
2. Issue `GET http://localhost:8080/fhir/Patient?identifier=S6474456`.
3. Response Bundle has `total >= 1` and entry `resource.id = "S6474456"` → store reference `Patient/S6474456`.
4. Construct Observation query using stored reference:
   `GET http://localhost:8080/fhir/Observation?code=K&patient=Patient/S6474456&_sort=-date&_count=1`.
5. Extract `valueQuantity.value` (or `valueString`) and `effectiveDateTime`.
6. Apply any downstream lab‑threshold logic.
7. Return `FINISH([value, date])` or place order as needed.

**Correct output:** `FINISH([3.9, "2023-11-12T14:07:00+00:00"])`
**Wrong output (missing patient prefix):** `GET ...&patient=S6474456...` → 400 error.

## Success Indicators
- A `GET /Patient` request appears **before** any `GET /Observation` that references the same MRN.
- The Observation request’s `patient=` parameter is exactly `Patient/{MRN}`.
- No 400 errors related to malformed patient references.
- The final `FINISH` payload contains the expected numeric value and ISO‑8601 timestamp (or appropriate order actions).

## Failure Indicators
- Observation query occurs before a successful Patient GET.
- Observation request uses `patient={MRN}` without the `Patient/` prefix.
- The agent finishes with a result before verifying patient existence.
- Repeated malformed Observation requests appear in the trace.
