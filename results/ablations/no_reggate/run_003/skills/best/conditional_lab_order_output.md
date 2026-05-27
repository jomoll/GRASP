---
description: "Ensures correct FINISH format and ordering flow for tasks that request\
  \ a lab value **and** include a conditional order clause (e.g., \"If low, then order\
  \ replacement ...\"). This skill now activates **only** when the task mentions a\
  \ specific lab identifier (name or LOINC code) **and** contains a low/high threshold\
  \ conditional phrase together with an order request, preventing interference with\
  \ unrelated \"If \u2026 then \u2026\" or pure order\u2011only tasks."
name: conditional_lab_order_output
provenance:
  action: ADD
  epoch: 4
  fixes: 7
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - task1_11
  - task10_13
  - task9_5
  - task8_21
  - task5_7
  - task10_10
  - task10_15
  - task1_26
  - task8_3
  - task9_11
  update_cycle: 1
tags: []
version: 1
---

# Conditional Lab Order Output (Narrowed Trigger)

## When to Activate
This skill should run **only** if **all** of the following are true in the task description:
1. **Lab identifier present** – a lab name (e.g., potassium, magnesium, sodium, creatinine, etc.) **or** a LOINC/code pattern (`code=`, `LOINC`, etc.).
2. **Conditional phrase present** – a low/high threshold clause such as:
   - "If low, then …"
   - "If below X, …"
   - "If the value is < X, …"
   - "If high, then …" (or similar wording).
3. **Order request present** – the task explicitly asks to place a `ServiceRequest` (medication, procedure, referral, follow‑up lab, etc.) when the condition is met.

If any of the three criteria are missing, the agent must **ignore** this skill and fall back to the default behavior.

---

## Core Procedure (executed only when the guard above passes)
1. **Extract the latest Observation**
   ```
   GET {api_base}/Observation?code={LAB_CODE}&patient={MRN}
   ```
   - Read `valueQuantity.value` → numeric value.
   - Store `effectiveDateTime` if needed later (do **not** include it in FINISH).
2. **Compare to the threshold** supplied in the task.
   - Use `<=` for "low" conditions, `>=` for "high" conditions.
3. **Conditional actions**
   - **If the condition is met**:
     1. POST the required `ServiceRequest` (medication, procedure, etc.).
     2. If the task also asks for a follow‑up lab, POST a second `ServiceRequest` for that lab.
     3. FINISH with a **single short string** confirming the action, e.g.:
        `FINISH(["Potassium replacement and follow‑up ordered"])`
   - **If the condition is NOT met**:
     - Do **no** POST.
     - FINISH with the **scalar numeric value only**, e.g.:
       `FINISH([4.7])`

---

## Formatting Rules
- The `FINISH` payload **must be a single JSON array** containing **exactly one element**:
  - One **number** (the lab value) **or**
  - One **string** (order confirmation).
- **Never** include timestamps, notes, or additional objects inside the FINISH array.
- All required `ServiceRequest` POSTs must appear **before** the FINISH call.

---

## Example
**Task:** "Check patient S1796597's most recent potassium level. If low (<3.5), order replacement potassium and schedule a repeat potassium lab for tomorrow 08:00."

**Execution:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1796597`
2. Extract `valueQuantity.value = 3.2`.
3. 3.2 < 3.5 → condition met.
4. POST `ServiceRequest` for potassium replacement.
5. POST `ServiceRequest` for follow‑up potassium lab (authoredOn = tomorrow 08:00).
6. `FINISH(["Potassium replacement and follow‑up ordered"])`

If the value had been 4.7, steps 4‑5 would be skipped and the agent would finish with `FINISH([4.7])`.

---

## Guard Clause Implementation (pseudocode for the agent)
```python
if (lab_identifier_present(task) and conditional_phrase_present(task) and order_request_present(task)):
    # run the conditional lab order logic above
else:
    # defer to other skills / default handling
```

---

## Success Indicators
- FINISH contains exactly one element (number **or** string).
- All required `ServiceRequest` POSTs appear **before** FINISH.
- No timestamps or extra data are embedded in the FINISH array.

---

## Failure Indicators
- FINISH array has more than one element or mixes types.
- Required POST(s) missing when the condition is met.
- FINISH includes timestamps, notes, or other objects.
- Skill triggered on a task that does **not** meet the three guard criteria.

---

*This revised version retains the original mechanism for handling conditional lab‑value tasks while adding a strict guard to prevent accidental activation on unrelated "If … then …" or pure order‑only instructions, thereby fixing the regressions observed in `task1_13` and `task8_14`.*
