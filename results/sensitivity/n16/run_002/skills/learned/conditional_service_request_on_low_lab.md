---
description: "Create a ServiceRequest when a recent lab Observation is below its low\u2011\
  threshold."
name: conditional_service_request_on_low_lab
provenance:
  action: ADD
  epoch: 2
  fixes: 3
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task9_9
  - task5_19
  - task4_26
  - task9_27
  - task10_18
  - task8_15
  - task2_16
  - task9_14
  - task9_3
  update_cycle: 1
tags: []
version: 1
---

# Conditional ServiceRequest Creation on Low Lab Value

## Pattern Description
You must translate a clinical rule that says *"If the latest lab value is low, order the replacement medication"* into concrete FHIR actions. After a GET Observation returns a bundle, extract the numeric result, compare it to a predefined low‑threshold for that lab code, and, only when the value is below the threshold, POST a `ServiceRequest` with the appropriate medication code (or NDC) and patient reference. If the bundle is empty or the value is not low, do nothing and finish.

## When to Use This Skill
- When a task asks to *check the most recent `<lab>` level* (e.g., magnesium, potassium) *and order replacement if low*.
- When the GET Observation query includes `code=<lab>` and a time filter (e.g., `date=ge...`).
- When the task description contains the word **low** and provides the replacement medication identifier (NDC or SNOMED) in the context.

## Common Failure Patterns
- Returning only the raw string value (e.g., `"2.2 mg/dL"`) and finishing without ordering.
- Ignoring the numeric comparison and always finishing.
- Posting a `ServiceRequest` with the wrong `code` (e.g., using the lab LOINC instead of the medication code).
- Posting a request even when the Observation bundle is empty.

## Recommended Patterns
**Pattern 1: Extract numeric value**
1. Inspect the GET response `Bundle.entry[0].resource.valueQuantity.value` (or `valueQuantity.value` if present). If the value is a string, strip non‑numeric characters and parse to a float.
2. Record the unit from `valueQuantity.unit` for sanity‑checking but do not include it in the comparison.

**Pattern 2: Determine low‑threshold**
- Use a hard‑coded map (can be extended later):
  ```json
  {
    "MG": 1.5,   // mg/dL
    "K": 3.5     // mmol/L
  }
  ```
- Retrieve the threshold for the observed `code` and compare: `if value < threshold` → low.

**Pattern 3: Build ServiceRequest**
1. Identify the replacement medication code from the task context (e.g., an NDC like `12345-6789-01`). If not explicitly given, fall back to a default mapping:
   ```json
   {"MG": "NDC_MG_REPLACEMENT", "K": "NDC_K_REPLACEMENT"}
   ```
2. POST to `/fhir/ServiceRequest` with:
   ```json
   {
     "resourceType": "ServiceRequest",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "code": {"coding":[{"system":"http://hl7.org/fhir/sid/ndc","code":"<NDC>","display":"<Medication>"}]},
     "subject": {"reference":"Patient/<MRN>"},
     "authoredOn": "<current ISO datetime>"
   }
   ```
3. After a successful POST, call `FINISH(["ServiceRequest created"])`.

**Pattern 4: No result or not low**
- If the bundle `total` is 0, or the extracted value is ≥ threshold, simply call `FINISH([])` (or return a placeholder like `-1` if the task expects a numeric answer).

## Example Application
**Task:** "Check patient S3057899's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S3057899&date=ge2023-11-12T10:15:00Z`
2. Response bundle contains an entry with `valueQuantity.value = 2.2` and `unit = "mg/dL"`.
3. Low‑threshold for `MG` is `1.5`. Since `2.2 >= 1.5`, the value is **not low** → `FINISH([])`.
4. If the value had been `1.2`, the agent would POST:
   ```json
   POST http://localhost:8080/fhir/ServiceRequest
   {
     "resourceType":"ServiceRequest",
     "status":"active",
     "intent":"order",
     "priority":"stat",
     "code":{"coding":[{"system":"http://hl7.org/fhir/sid/ndc","code":"NDC_MG_REPLACEMENT","display":"IV Magnesium"}]},
     "subject":{"reference":"Patient/S3057899"},
     "authoredOn":"2023-11-13T10:15:00+00:00"
   }
   ```
   Then `FINISH(["ServiceRequest created"])`.

## Success Indicators
- The agent posts a `ServiceRequest` **only** when the extracted numeric value is below the mapped low‑threshold.
- The POST body contains the correct medication NDC/code and the patient MRN.
- The final `FINISH` output reflects the action taken (e.g., `ServiceRequest created` or empty list).

## Failure Indicators
- A `ServiceRequest` is posted when the observation bundle is empty or the value is normal/high.
- The agent finishes without posting despite a low value.
- The posted `ServiceRequest` uses the lab LOINC code instead of the medication NDC.
- The numeric extraction fails (e.g., returns a string) and the comparison is skipped.
