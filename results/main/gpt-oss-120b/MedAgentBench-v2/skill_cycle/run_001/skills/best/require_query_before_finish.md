---
description: Enforce a GET request before any FINISH action when the task needs data
  retrieval
name: require_query_before_finish
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 6
  regressions: 2
  triggering_sample_ids:
  - task6_20
  - task10_12
  - task6_3
  - task9_11
  - task1_15
  - task3_14
  - task4_11
  - task9_14
  - task3_7
  - task1_12
  update_cycle: 0
tags: []
version: 1
---

# Require Query Before Finish

## Pattern Description
You must never finish a task (issue a `FINISH` action) until you have queried the FHIR server for the data that the instruction asks for. This rule applies to any instruction that mentions retrieving lab results, procedures, medication orders, vaccinations, or any other clinical resource. The purpose is to prevent the agent from fabricating answers without evidence and to ensure that downstream decisions are based on real data.

## When to Use This Skill
- When the instruction contains keywords like **"most recent", "date of", "value of", "check if", "verify", "review", "determine"** followed by a FHIR resource name (Observation, Procedure, MedicationRequest, ServiceRequest, etc.).
- When the agent is about to emit a `FINISH` action and the action history does **not** contain a preceding `GET` request for the relevant resource type.
- When the instruction explicitly asks to **order** something *based on* a lab value or prior procedure, which implies a prior data lookup.

## Common Failure Patterns
- `FINISH` is issued immediately without any preceding `GET` request.
- A `GET` request is issued **after** `FINISH`, which never reaches the agent.
- The agent performs a `GET` for the wrong resource (e.g., MedicationRequest when the task required Observation).
- The agent uses a hard‑coded answer like "No prior record found" without verifying via a query.

## Recommended Patterns
**Pattern 1: Verify query existence before finishing**
1. Scan the action log for the current task.
2. If the next action is `FINISH` **and** there is no earlier `GET` whose URL contains the patient identifier and a relevant `code` or `resource` parameter, **block** the `FINISH`.
3. Instead, construct a `GET` request that matches the instruction:
   - For lab values: `GET /Observation?code={CODE}&patient={PATIENT_ID}`
   - For procedures: `GET /Procedure?code={CODE}&patient={PATIENT_ID}`
   - For medication orders: `GET /MedicationRequest?patient={PATIENT_ID}`
   - For vaccination status: `GET /Procedure?code=COVIDVACCINE&patient={PATIENT_ID}`
4. After receiving the response, continue with the decision logic and only then issue `FINISH`.

**Pattern 2: Fallback when the required resource type is ambiguous**
- If the instruction does not name a specific code, infer the most likely resource from context (e.g., "TSH" → Observation, "CT Abdomen" → Procedure).
- Issue a generic `GET` for the patient and filter client‑side if needed.

**Pattern 3: Formatting the final output**
- The `FINISH` payload must contain only the answer text (or JSON array) **without** raw API responses.
- Example of correct output: `FINISH(["Latest TSH = 3.2 uIU/mL; no action required."])`
- Example of wrong output: `FINISH(["GET returned 0 entries; ordering new test."])`

## Example Application
**Task:** "Retrieve the most recent TSH and free T4 values for patient S0547588 and act according to protocol."

**Step‑by‑step:**
1. Detect that the task mentions lab codes `TSH` and `FT4` → need Observation data.
2. Before any `FINISH`, issue:
   ```
   GET http://localhost:8080/fhir/Observation?code=TSH&patient=S0547588
   GET http://localhost:8080/fhir/Observation?code=FT4&patient=S0547588
   ```
3. Parse the returned bundles, extract the most recent `valueQuantity.value` for each.
4. Apply the protocol logic (e.g., if TSH > 10 uIU/mL, order repeat labs).
5. Only after the decision is made, emit:
   ```
   FINISH(["Latest TSH = 4.1 uIU/mL, FT4 = 1.2 ng/dL; no medication change needed."])
   ```

## Success Indicators
- Every `FINISH` action is preceded by at least one `GET` that matches the patient and resource hinted by the instruction.
- The agent’s answer references actual values extracted from the GET response.
- No `FINISH` occurs when the action log shows only `THINK` or `ANSWER` steps.

## Failure Indicators
- `FINISH` appears with no prior `GET` for the required resource.
- The agent fabricates a result (e.g., "No prior record found") without showing a query.
- The agent queries a different resource type than what the instruction demands.
