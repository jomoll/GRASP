---
description: "Validate that vital\u2011sign Observation resources contain the required\
  \ units in valueString"
name: vital_signs_observation_units_validation
provenance:
  action: ADD
  epoch: 0
  fixes: 21
  probe_score: 4
  regressions: 3
  triggering_sample_ids:
  - task9_1
  - task4_7
  - task3_16
  - task4_26
  - task10_18
  - task1_20
  - task4_20
  - task9_20
  - task3_30
  - task10_16
  update_cycle: 1
tags:
- validation
- vital-signs
- units
version: 1
---

# Vital Signs Observation Units Validation

## Pattern Description
You must ensure that any Observation you create for a vital sign includes the appropriate unit suffix in its `valueString`.  The FHIR `Observation.valueString` field is free‑text, but downstream consumers (clinical dashboards, decision rules) rely on the unit being present (e.g., "mmHg" for blood pressure, "bpm" for heart rate).  Missing units cause validation failures and downstream logic to mis‑interpret the measurement.

## When to Use This Skill
- When constructing a **POST** to `/Observation` for a vital‑sign code (e.g., BP, HR, RR, SpO₂).
- When the task description supplies a measurement value **without** an explicit unit.
- When the `valueString` you are about to send does not already contain the expected unit token.

## Common Failure Patterns
- `valueString: "118/77"` – blood‑pressure missing "mmHg".
- `valueString: "72"` – heart‑rate missing "bpm".
- `valueString: "98%"` – SpO₂ already has "%" (acceptable) – but missing for other signs.
- Using the wrong unit (e.g., "kPa" for BP) when the system expects "mmHg".

## Recommended Patterns
**Pattern 1: Detect required unit**
1. Identify the vital‑sign code you are posting (`code.text` or a coding system).
2. Map the code to its required unit token:
   - `BP` → `mmHg`
   - `HR` → `bpm`
   - `RR` → `breaths/min`
   - `SpO2` → `%` (already part of value, but verify presence)
3. Inspect the candidate `valueString`.
   - If it already ends with the required token, **proceed**.
   - If it does **not**, append a space and the required token.

**Pattern 2: Fallback / verification**
- If the task explicitly supplies the unit, trust it.
- If the unit is ambiguous, log a warning and use the default mapping.
- After modification, re‑validate that the string now contains the token.

**Pattern 3: Formatting the final Observation**
```json
{
  "resourceType": "Observation",
  "category": [{"coding": [{"system": "http://hl7.org/fhir/observation-category","code": "vital-signs","display": "Vital Signs"}]}],
  "code": {"text": "BP"},
  "effectiveDateTime": "2023-11-13T10:15:00+00:00",
  "status": "final",
  "valueString": "118/77 mmHg",   // <-- unit guaranteed
  "subject": {"reference": "Patient/S1234567"}
}
```

## Example Application
**Task:** "I just measured the blood pressure for patient S1234567, and it is \"118/77\". Help me record it."

**Step‑by‑step:**
1. Extract the measurement value "118/77" from the instruction.
2. Recognise the vital‑sign code is BP (flowsheet ID "BP").
3. Look up required unit → `mmHg`.
4. Check `valueString` – it lacks `mmHg` → append.
5. Build the Observation JSON with `valueString: "118/77 mmHg"`.
6. POST to `/Observation` and call `FINISH`.

**CORRECT output:**
```json
POST /fhir/Observation { ... "valueString": "118/77 mmHg", ... }
FINISH([])
```
**WRONG output:**
```json
POST /fhir/Observation { ... "valueString": "118/77", ... }
FINISH([])
```

## Success Indicators
- The POST body contains `valueString` that ends with the expected unit token.
- System verification log shows the Observation stored with the unit present.
- No validation error about missing units is reported.

## Failure Indicators
- The posted Observation’s `valueString` does not contain the required unit (e.g., "118/77").
- System notes flag "observation_value_missing_units".
- Downstream logic that expects a unit fails or returns incorrect results.
