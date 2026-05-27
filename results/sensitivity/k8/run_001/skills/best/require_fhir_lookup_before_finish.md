---
description: Force a GET request for the needed FHIR resource before emitting any
  FINISH answer.
name: require_fhir_lookup_before_finish
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 15
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task9_14
  - task3_7
  - task9_27
  - task4_20
  update_cycle: 0
tags:
- pre_answer_check
- fhir_lookup
- required_action
version: 1
---

# Require FHIR Lookup Before FINISH

## Pattern Description
You must never answer a clinical question (FINISH) that depends on patient data without first retrieving that data from the FHIR server. For any task that mentions a patient identifier, a lab code, a vital‑sign flowsheet, or a need to compute age, the first step must be a GET request that fetches the required resource. Only after the GET response is available should you extract the needed field and construct the final answer or subsequent POST.

## When to Use This Skill
- When the instruction asks for a value that lives in a FHIR resource (e.g., "most recent potassium level", "patient age", "record blood pressure").
- When the instruction includes a patient MRN/identifier that must be resolved to a FHIR Patient ID.
- When the instruction requires a conditional order based on a lab result.
- When the agent is about to emit `FINISH` without having performed a preceding `GET` for the relevant resource.

## Common Failure Patterns
- Direct `FINISH([...])` with a computed value but no prior `GET` request.
- `FINISH` after a `POST` that creates a resource but the patient reference was never verified via `GET /Patient`.
- Missing `GET` for an Observation when the task asks "most recent X level".
- Using hard‑coded values instead of extracting from the GET response.

## Recommended Patterns
**Pattern 1: Detect missing lookup**
1. Scan the task description for keywords: `patient`, `MRN`, `identifier`, lab `code`, flowsheet `ID`, `age`, `level`, `value`.
2. Determine the required FHIR endpoint:
   - Patient lookup → `GET {api_base}/Patient?identifier={MRN}` (or family/given/birthdate when name/DOB provided).
   - Observation lookup → `GET {api_base}/Observation?code={CODE}&patient={MRN}` (add `date` filters if time‑bounded).
3. If no `GET` action for that endpoint appears earlier in the turn sequence, **do not** emit `FINISH`. Instead output the appropriate `GET` request.

**Pattern 2: Perform the lookup**
- Output the exact URL and query parameters in the required format, e.g.: `GET http://localhost:8080/fhir/Patient?identifier=S123456` or `GET http://localhost:8080/fhir/Observation?code=K&patient=S123456`.
- Wait for the system to return the response before proceeding.

**Pattern 3: After successful GET, extract and answer**
1. Parse the returned Bundle to locate the first entry (most recent) and the field of interest (`valueQuantity.value`, `valueQuantity.unit`, `effectiveDateTime`, `birthDate`).
2. Perform any required calculation (e.g., age = floor(currentDate - birthDate)).
3. Construct the final `FINISH` payload using only the extracted primitive values, no explanatory text.

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"

**Step‑by‑step:**
1. Detect need for patient data → required endpoint `GET /Patient?identifier=S2874099`.
2. Output: `GET http://localhost:8080/fhir/Patient?identifier=S2874099`.
3. Receive Bundle, extract `birthDate` (e.g., `1950-04-12`).
4. Compute age = floor(`2023-11-13` – `1950-04-12`) = 73.
5. Output: `FINISH([73])`.

**Task:** "Check patient S1715871's last serum magnesium level within last 24 hours. If low, order replacement."

**Step‑by‑step:**
1. Need Observation → `GET /Observation?code=MG&patient=S1715871` (add date filter if required).
2. Output the GET request.
3. Parse response; if `total == 0` → `FINISH(["No serum magnesium level recorded in the last 24 hours. No magnesium replacement ordered."])`.
4. If a value exists and is below threshold, follow the ordering flow (POST) after the GET.

## Success Indicators
- Every `FINISH` is preceded in the same turn sequence by a `GET` that matches the resource needed for the answer.
- The `FINISH` payload contains only the extracted primitive (number, string, or array) without extra explanation.
- Conditional orders are only issued after the observation GET has been performed and evaluated.

## Failure Indicators
- `FINISH` appears without any prior `GET` for the required patient or observation.
- The agent uses hard‑coded numbers or strings instead of values from the GET response.
- The GET request targets the wrong resource (e.g., `GET /Condition` when a Patient lookup is needed).
