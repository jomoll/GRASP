---
description: Ensure correct FHIR resource type and subject reference when creating
  medication and service orders
name: order_resource_type_and_subject_reference_for_medication_and_service_requests
provenance:
  action: ADD
  epoch: 1
  fixes: 6
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task9_22
  - task2_22
  - task8_7
  - task4_27
  - task2_26
  - task3_17
  - task2_1
  - task8_29
  - task2_30
  - task3_3
  update_cycle: 0
tags:
- FHIR
- order
- resource type
- subject reference
- MedicationRequest
- ServiceRequest
- vaccine
- prophylaxis
version: 1
---

# Order Resource Type and Subject Reference for Medication and Service Requests

## Pattern Description

When creating orders in FHIR, it is essential to use the correct resource type and subject reference format based on the clinical context. Medication orders (such as vaccines, DVT prophylaxis, or naloxone) must use the `MedicationRequest` resource, while non-medication procedures (such as imaging studies or device removals) typically use the `ServiceRequest` resource. Additionally, the `subject.reference` field must always be formatted as `Patient/{id}` (not just the patient ID or other variants).

Failure to use the correct resource type or subject reference format can result in orders not being stored, not retrievable, or not actionable by downstream systems. This skill ensures that the agent reliably selects the right resource and reference format for each order type.

## When to Use This Skill

- When creating a new order for a medication, vaccine, or prophylaxis (e.g., influenza vaccine, COVID-19 booster, heparin for DVT prophylaxis, naloxone)
- When creating a new order for a non-medication procedure or service (e.g., imaging, catheter removal)
- Whenever constructing a FHIR order POST body that includes a `subject` field

## Common Failure Patterns

- Using `ServiceRequest` instead of `MedicationRequest` for medication or vaccine orders
- Using `MedicationRequest` for non-medication procedures (e.g., imaging, device removal)
- Setting `subject.reference` to just the patient ID (e.g., `"S2090974"`) instead of `"Patient/S2090974"`
- Omitting the `Patient/` prefix in the subject reference
- POSTing an order that is accepted but not retrievable due to resource type or reference errors

## Recommended Patterns

**Pattern 1: Resource Type Selection**
- For medication, vaccine, or prophylaxis orders: use `MedicationRequest`.
- For non-medication procedures or services: use `ServiceRequest`.

CORRECT: `POST /MedicationRequest` for influenza vaccine order
WRONG:   `POST /ServiceRequest` for influenza vaccine order

**Pattern 2: Subject Reference Formatting**
- Always set `subject.reference` to `"Patient/{id}"` (e.g., `"Patient/S2090974"`).
- Do not use just the patient ID or any other format.

CORRECT: `"subject": { "reference": "Patient/S2090974" }`
WRONG:   `"subject": { "reference": "S2090974" }`

**Pattern 3: Verification Before POST**
- Before POSTing, check that the resource type matches the order type and that `subject.reference` is correctly formatted.

## Example Application

**Task:** "Determine the date of the last influenza vaccine for patient S2090974. If it was administered more than 365 days ago, order a new influenza vaccine for today."

**Step-by-step:**

1. Issue GET `/Procedure?code=90686&patient=S2090974` to check for prior vaccine.
2. If no recent vaccine, construct a `MedicationRequest`:
   - `resourceType`: `MedicationRequest`
   - `medicationCodeableConcept.coding`: CPT code 90686
   - `subject.reference`: `Patient/S2090974`
   - Include dosage, route, and other required fields
3. POST to `/MedicationRequest` endpoint.

CORRECT POST body:
```json
{
  "resourceType": "MedicationRequest",
  "medicationCodeableConcept": {
    "coding": [
      { "system": "http://www.ama-assn.org/go/cpt", "code": "90686", "display": "Influenza vaccine, quadrivalent, preservative-free, IM" }
    ],
    "text": "influenza vaccine (quadrivalent, preservative-free, IM)"
  },
  "authoredOn": "2024-01-09",
  "dosageInstruction": [
    { "route": { "text": "IM" }, "doseAndRate": [ { "doseQuantity": { "value": 0.5, "unit": "mL" } } ] }
  ],
  "status": "active",
  "intent": "order",
  "subject": { "reference": "Patient/S2090974" }
}
```

WRONG POST body:
```json
{
  "resourceType": "ServiceRequest",
  ...
  "subject": { "reference": "S2090974" }
}
```

## Success Indicators

- Orders for medications and vaccines are always created as `MedicationRequest` resources.
- Orders for non-medication procedures are created as `ServiceRequest` resources.
- All `subject.reference` fields are in the format `Patient/{id}`.
- Orders are retrievable after POST and accepted by downstream systems.

## Failure Indicators

- Orders are accepted on POST but not found on retrieval (resource not stored due to type/reference error).
- Orders for medications/vaccines appear as `ServiceRequest` resources.
- `subject.reference` is missing the `Patient/` prefix or is just the patient ID.
- Downstream systems reject or ignore orders due to resource type or reference format.
