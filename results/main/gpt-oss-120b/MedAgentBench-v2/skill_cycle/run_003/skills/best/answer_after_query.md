---
description: Prevent the agent from answering or reasoning before a GET request response
  is received
name: answer_after_query
provenance:
  action: ADD
  epoch: 0
  fixes: 6
  probe_score: 7
  regressions: 0
  triggering_sample_ids:
  - task2_30
  - task8_23
  - task9_8
  - task3_1
  - task1_11
  - task2_14
  - task9_14
  - task1_6
  - task2_1
  - task3_10
  update_cycle: 0
tags:
- query
- response
- control
version: 1
---

# Answer After Query Enforcement

## Pattern Description
You must never produce a final answer, recommendation, or any reasoning that depends on data **before** you have received the response to a GET request you issued. This rule applies to any task that requires verification of existing FHIR resources (e.g., MedicationRequest, Observation, Procedure, ServiceRequest). The agent’s workflow is: 1) construct and send the GET request, 2) **wait** for the user to supply the JSON bundle response, 3) extract the needed fields, 4) make a decision, and finally 5) issue POST/PUT actions or `FINISH`.

## When to Use This Skill
- Whenever you issue a `GET http://.../fhir/...` request.
- When the task instruction says *"verify", "find", "retrieve", "determine"* and the answer depends on the returned data.
- Before any `FINISH([...])` or any free‑text answer that references values from the server.

## Common Failure Patterns
- Providing a `FINISH` or explanatory text immediately after the `GET` line, without waiting for the response.
- Using placeholder reasoning like *"We need to verify…"* and then concluding the task.
- Mixing a POST request with a `FINISH` in the same turn before the GET response arrives.

## Recommended Patterns
**Pattern 1: Issue GET and pause**
1. Emit the exact `GET` URL you need, e.g. `GET http://localhost:8080/fhir/MedicationRequest?patient=S123456`.
2. **Do not** add any other output in the same message.
3. Wait for the user to reply with *"Here is the response from the GET request: { … }"*.

**Pattern 2: Verify response received**
1. Look for a user message that contains a JSON bundle with `resourceType":"Bundle"`.
2. If the bundle is missing or malformed, request clarification before proceeding.

**Pattern 3: Extract and decide**
1. Parse the bundle, locate the relevant entries (e.g., `entry[].resource.medicationCodeableConcept.text`).
2. Apply the task‑specific logic (count active orders, compare dates, evaluate lab values).
3. Only now may you issue POST/PUT actions or a `FINISH`.

**Pattern 4: Formatting the final output**
- `FINISH(["Your concise answer here"])` – a JSON array of strings, no extra commentary.
- Never embed raw JSON bundles or full resource representations in the `FINISH` payload.

## Example Application
**Task:** "Verify that patient S6227720 has exactly one active DVT prophylaxis order. If there are zero orders, create one. If there are multiple orders, discontinue duplicates keeping only the newest."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/MedicationRequest?patient=S6227720`
2. *[wait for user response]*
3. Parse the bundle; count entries where `status == "active"` and `medicationCodeableConcept.text` contains "heparin".
4. If count == 0 → `POST` a new MedicationRequest.
5. If count > 1 → identify the newest (`authoredOn`), `POST` a `MedicationRequest` with `status: "cancelled"` for the older ones.
6. `FINISH(["Created heparin prophylaxis order; now exactly one active order present."])`

## Success Indicators
- The agent’s first message after a task that needs data is **only** a GET request.
- The agent waits for a user‑provided bundle before any further action.
- All decisions are based on fields extracted from the received bundle.
- The final `FINISH` contains a concise answer without extraneous reasoning.

## Failure Indicators
- `FINISH` appears in the same turn as a `GET`.
- The agent references lab values or dates that were never supplied.
- The agent posts a new resource before confirming the current state from the GET response.
- The output includes free‑text explanations mixed with the `FINISH` array.
