---
description: Return a concise confirmation after creating an order instead of echoing
  the note
name: order_confirmation_output
provenance:
  action: ADD
  epoch: 1
  no_gate: true
  triggering_sample_ids:
  - task8_19
  - task9_22
  - task8_3
  - task8_21
  - task9_1
  - task9_5
  - task10_27
  - task8_7
  - task8_9
  - task1_20
  update_cycle: 1
tags:
- order
- confirmation
- servicerequest
version: 1
---

# Order Confirmation Output

## Pattern Description
You must provide a short, human‑readable confirmation after successfully creating an order (e.g., ServiceRequest, MedicationRequest, ProcedureRequest). The confirmation should identify the order type, the patient identifier, and the order status, without echoing any free‑text note content. This keeps the agent’s final answer focused on confirming that the requested action was performed.

## When to Use This Skill
- Immediately after a successful POST of a **ServiceRequest** (or similar order resource) and before issuing `FINISH`.
- When the task description asks for an order to be placed and expects a confirmation rather than the note payload.
- If the POST response includes a `status` of `active`/`completed` and a resource `id`.

## Common Failure Patterns
- `FINISH(["<note text>"])` – the agent returns the note field instead of a confirmation.
- `FINISH([])` or `FINISH([null])` – the agent provides no output after the order.
- Including the entire POST body in the FINISH output rather than a concise message.

## Recommended Patterns
**Pattern 1: Core confirmation construction**
1. Verify the POST response contains `resourceType` and a successful HTTP status (2xx).
2. Extract the order display name:
   - Prefer `code.coding[0].display` if present.
   - Fallback to `code.text`.
3. Extract the patient identifier from `subject.reference` (e.g., `Patient/S123456`).
4. Build the confirmation string:
   ```
   "<OrderDisplay> order created for patient <PatientID>."
   ```
   Example: `"Orthopedic surgery referral order created for patient S6530813."`
5. Call `FINISH(["<confirmation string>"])`.

**Pattern 2: Fallback when order type cannot be determined**
- If step 2 fails, use a generic message:
  ```
  "Order successfully created for patient <PatientID>."
  ```

**Pattern 3: Formatting rule**
- The FINISH payload must be a JSON array containing a single string.
- Do **not** include any note text, raw JSON, or additional fields.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S6530813. Include the specified free‑text in the note."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S6530813` – obtain patient.
2. `POST http://localhost:8080/fhir/ServiceRequest` with the required body (including the `note` field).
3. Receive POST response (e.g., `{ "resourceType": "ServiceRequest", "id": "abc123", "status": "active", "code": { "coding": [{ "display": "Orthopedic surgery referral" }] }, "subject": { "reference": "Patient/S6530813" } }`).
4. Apply Pattern 1: extract display = "Orthopedic surgery referral", patient = "S6530813".
5. Construct confirmation: `"Orthopedic surgery referral order created for patient S6530813."`
6. `FINISH(["Orthopedic surgery referral order created for patient S6530813."])`.

**CORRECT output:** `FINISH(["Orthopedic surgery referral order created for patient S6530813."])`
**WRONG output:** `FINISH(["Situation: acute left knee injury, …"])`

## Success Indicators
- The final `FINISH` call contains a single‑string array with a confirmation message.
- No note text appears in the output.
- The message correctly references the order type and patient identifier.

## Failure Indicators
- The `FINISH` payload includes the note text or raw POST body.
- The output array is empty or contains more than one element.
- The confirmation message is missing the patient identifier or order type.
