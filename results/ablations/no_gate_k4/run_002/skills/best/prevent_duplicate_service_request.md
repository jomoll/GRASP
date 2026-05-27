---
description: Avoid creating duplicate ServiceRequest resources for the same patient
  and code
name: prevent_duplicate_service_request
provenance:
  action: ADD
  epoch: 4
  no_gate: true
  triggering_sample_ids:
  - task10_13
  - task9_5
  - task9_22
  - task5_7
  - task10_10
  - task1_10
  - task5_3
  - task10_15
  - task10_18
  - task5_17
  update_cycle: 1
tags:
- order
- duplicate-prevention
- servicerequest
version: 1
---

# Prevent Duplicate ServiceRequest

## Pattern Description
You must ensure that you never create a duplicate `ServiceRequest` for the same patient and the same clinical code. Before issuing any `POST /ServiceRequest`, first search the FHIR server for an active request that matches the patient reference and the exact code (e.g., NDC, LOINC, or SNOMED). If such a request already exists, skip the creation and report that the order is already present. This pattern prevents the "duplicate_order_created" failure mode and keeps the order set clean.

## When to Use This Skill
- When the task instructs you to **order** a medication, lab, referral, or any other service via a `ServiceRequest`.
- The instruction may be executed multiple times (e.g., in loops, retries, or follow‑up checks).
- The patient identifier (`Patient/{MRN}`) and the service code are known from the task description.

## Common Failure Patterns
- Directly `POST` a `ServiceRequest` without checking for an existing one, resulting in two identical orders.
- Using only the `code.coding.code` value but omitting the `system` when searching, causing the search to miss existing orders.
- Ignoring the `status` field and treating a completed request as absent, leading to unnecessary re‑ordering.

## Recommended Patterns
**Pattern 1: Pre‑order existence check**
1. Construct a GET query:
   ```
   GET {base}/ServiceRequest?patient=Patient/{MRN}&code={system}|{code}&status=active
   ```
   - Replace `{system}` with the coding system (e.g., `http://hl7.org/fhir/sid/ndc`).
   - Replace `{code}` with the exact code value (e.g., `40032-917-01`).
2. Inspect the returned Bundle:
   - `total > 0` → an active order already exists.
   - `total == 0` → no active order; safe to create.

**Pattern 2: Conditional POST**
- **If an active order exists**:
  - Do **not** issue the `POST`.
  - Optionally add a note to the FINISH output, e.g., `"potassium replacement already ordered"`.
- **If no active order exists**:
  - Proceed with the original `POST` payload.

**Pattern 3: FINISH formatting**
- Always return a scalar list of messages, e.g.:
  - `FINISH(["potassium replacement ordered"])`
  - `FINISH(["potassium replacement already exists"])`

## Example Application
**Task:** "Check patient S6550627's most recent potassium level. If low, then order replacement potassium 40 mEq oral."

**Step‑by‑step:**
1. **GET latest potassium level** (as usual).
2. **Determine need for replacement** (value < threshold).
3. **Search for existing order**:
   ```
   GET http://localhost:8080/fhir/ServiceRequest?patient=Patient/S6550627&code=http://hl7.org/fhir/sid/ndc|40032-917-01&status=active
   ```
4. **If `total == 0`**, POST the new `ServiceRequest`.
5. **If `total > 0`**, skip POST.
6. **FINISH** with an appropriate message.

**Correct output when no prior order:**
```
FINISH(["potassium replacement ordered"])
```
**Correct output when order already exists:**
```
FINISH(["potassium replacement already exists"])
```

## Success Indicators
- Only one `POST /ServiceRequest` for a given patient/code pair appears in the logs.
- FINISH output reflects whether a new order was created or an existing one was found.
- No "Warning: ServiceRequest POST accepted but resource not found" messages related to duplicate creation.

## Failure Indicators
- Two `POST /ServiceRequest` calls with identical `code` and `patient` appear.
- FINISH reports ordering while a prior identical request is still present in the system.
- Duplicate orders cause downstream alerts or resource‑not‑found warnings.
