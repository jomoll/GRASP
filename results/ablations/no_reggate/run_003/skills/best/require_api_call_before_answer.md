---
description: Force a GET request for needed FHIR data before providing any answer
  or order.
name: require_api_call_before_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 2
  probe_score: 4
  regressions: 3
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task9_14
  - task3_7
  update_cycle: 0
tags:
- api
- validation
- data_fetch
version: 1
---

# Require API Retrieval Before Answer

## Pattern Description
You must never answer a clinical question or place an order that depends on patient‑specific data without first retrieving that data from the FHIR server. The agent should treat every request for a value (age, lab result, vital sign, etc.) as a two‑step process: **fetch** the resource, **process** the response, then **respond**. This prevents stale or guessed answers and guarantees that the information used is the latest available.

## When to Use This Skill
- Any task that asks for a patient attribute (age, MRN, name, etc.).
- Any task that requests the most recent Observation, Condition, Medication, or ServiceRequest.
- When the instruction includes a conditional action based on a lab value, vital sign, or date.
- When the task mentions a specific code (e.g., `code=MG`, `code=K`, `code=A1C`).

## Common Failure Patterns
- Agent issues `FINISH([...])` or writes a response without a preceding `GET …` call.
- Agent assumes a resource exists and extracts fields from an empty bundle.
- Agent returns a placeholder like `-1` or a hard‑coded string without verification.
- Agent includes order details in the answer even though the required lab result was never fetched.

## Recommended Patterns
**Pattern 1: Identify and fetch the required resource**
1. Parse the instruction to determine the needed FHIR resource type (Patient, Observation, etc.) and search parameters (identifier, code, date, etc.).
2. Construct the exact GET URL, e.g.:
   - `GET {api_base}/Patient?identifier=S123456`
   - `GET {api_base}/Observation?code=MG&patient=S123456&date=ge2023-11-12T10:15:00Z`
3. Emit the GET request as the sole action for the turn.

**Pattern 2: Verify the response before proceeding**
1. Wait for the server’s Bundle response.
2. If `total == 0` (no matching entries), treat the value as *not recorded* and follow the “no data” branch of the instruction.
3. If entries exist, extract the exact field required:
   - For age: `entry[0].resource.birthDate`
   - For a numeric lab: `entry[0].resource.valueQuantity.value`
   - For a vital sign string: `entry[0].resource.valueString`
4. Perform any unit conversion or date comparison needed.

**Pattern 3: Respond only after a successful fetch**
1. After extraction, construct the final answer or order.
2. Use `FINISH([...])` **only** after the GET (and any subsequent POST) have been completed.
3. Do **not** embed order messages in the answer when the prerequisite data was missing.

## Example Application
**Task:** "Check patient S0636132's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium. If no magnesium level recorded, do nothing."

**Step‑by‑step:**
1. Identify needed resource → Observation with `code=MG` for patient `S0636132` and date filter `ge2023-11-12T10:15:00Z`.
2. Emit: `GET http://localhost:8080/fhir/Observation?code=MG&patient=S0636132&date=ge2023-11-12T10:15:00Z`
3. Receive Bundle. If `total == 0`, `FINISH(["No serum magnesium level recorded; no IV magnesium ordered."])`.
4. If a result exists, extract `valueQuantity.value` and compare to the low‑threshold.
5. If low, POST a ServiceRequest for magnesium replacement, then `FINISH(["IV magnesium ordered."])`.

## Success Indicators
- A `GET` line appears **before** any `FINISH` or order construction.
- The GET URL contains the correct resource type and query parameters.
- The agent checks `total` in the Bundle and branches accordingly.
- The final answer references data extracted from the GET response.

## Failure Indicators
- `FINISH` is emitted without a preceding `GET`.
- The GET URL is missing required parameters (e.g., no `code` for Observation).
- The agent proceeds with a hard‑coded value or placeholder.
- Order messages are included when the required observation was never fetched.
