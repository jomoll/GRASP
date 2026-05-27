---
description: Force a GET request for any needed FHIR resource before answering or
  creating a resource.
name: require_fhir_query_before_answer
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 0
  fixes_unused: 6
  probe_score_unused: 2
  regressions_unused: 2
  triggering_sample_ids:
  - task3_14
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task3_30
  - task4_28
  - task4_7
  - task8_5
  update_cycle: 0
tags: []
version: 1
---

# Require FHIR Query Before Answer

## Pattern Description
You must always retrieve the required FHIR resource **before** you produce any answer, create a new resource, or finish the task. The agent should first issue a GET request that resolves the identifier(s) mentioned in the instruction (e.g., patient MRN, observation code, flowsheet ID, lab LOINC, etc.). Only after a successful response can you extract IDs, values, or timestamps and use them in subsequent POST/PUT actions or in the final FINISH output. This prevents missing‑patient‑lookup errors and ensures that all downstream actions are based on verified data.

## When to Use This Skill
- When the instruction references a patient by MRN, name, or other identifier.
- When the instruction asks for a lab/observation value (e.g., "most recent magnesium level", "HbA1c value").
- When the instruction requires creating a resource that needs a patient reference (Observation, ServiceRequest, MedicationRequest, etc.).
- When the instruction includes a code, flowsheet ID, or LOINC that must be looked up via a FHIR search.

## Common Failure Patterns
- Directly issuing a POST Observation or ServiceRequest without first GETting the Patient.
- Answering a value‑based question (age, lab result) without first GETting the Observation/Patient.
- Using a hard‑coded patient reference like `Patient/S12345` without confirming the ID exists.
- Skipping the GET even when the task explicitly mentions a code or identifier.

## Recommended Patterns
**Pattern 1: Identify required resource and issue GET**
1. Scan the task text for identifiers:
   - `MRN`, `identifier=`, `patient`, `name`, `DOB` → need **Patient**.
   - `code=`, `flowsheet ID`, `LOINC`, `lab` → need **Observation** (or **Condition**, **MedicationRequest**, etc.).
2. Build the GET URL using the base URL from the environment:
   - Patient: `GET {api_base}/Patient?identifier={MRN}`
   - Observation: `GET {api_base}/Observation?code={CODE}&patient={MRN}[&date=ge{START}]`
   - Adjust date filters to ISO‑8601 (`ge2023-11-12T10:15:00Z`).
3. Issue the GET request **as the very next action**.
4. Wait for the response before proceeding.

**Pattern 2: Verify GET response before proceeding**
- If `total == 0` → treat as “not found” and either abort with a clear FINISH message or follow the task’s fallback (e.g., do not order medication).
- If `total > 0` → extract the needed field (`id`, `valueQuantity.value`, `effectiveDateTime`, etc.).

**Pattern 3: Use extracted data in subsequent actions**
- For POST resources, reference the patient as `"reference": "Patient/{id}"` where `{id}` comes from the GET response.
- For answer formatting, output only the required primitive (e.g., a number or string) without extra explanatory text.

## Example Application
**Task:** "I just measured the blood pressure for patient with MRN of S1579803, and it is \"118/77 mmHg\". Help me record it."

**Step‑by‑step:**
1. Detect that a patient MRN is needed → GET Patient.
   ```
   GET http://localhost:8080/fhir/Patient?identifier=S1579803
   ```
2. Receive response, extract the patient ID (e.g., `S1579803`).
3. Construct Observation POST using the extracted ID:
   ```
   POST http://localhost:8080/fhir/Observation
   {
     "resourceType": "Observation",
     "category": [{"coding":[{"system":"http://hl7.org/fhir/observation-category","code":"vital-signs"}]}],
     "code": {"text": "BP"},
     "effectiveDateTime": "2023-11-13T10:15:00+00:00",
     "status": "final",
     "valueString": "118/77 mmHg",
     "subject": {"reference": "Patient/S1579803"}
   }
   ```
4. FINISH with the required concise output:
   ```
   FINISH(["Blood pressure 118/77 mmHg recorded for patient S1579803 at 2023-11-13T10:15:00+00:00."])
   ```

## Success Indicators
- The first action after receiving the task is a GET request for the needed resource.
- The GET response is inspected and its fields are used in any later POST or FINISH.
- No POST or FINISH appears before the corresponding GET.

## Failure Indicators
- A POST or FINISH occurs without a preceding GET for the same patient/observation.
- The agent references a hard‑coded patient ID that was never verified.
- The final answer includes extra explanatory text beyond the required format.
