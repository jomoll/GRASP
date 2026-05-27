---
description: "Add a strict guard so the skill only activates for tasks that explicitly\
  \ request a low\u2011lab\u2011value replacement order (e.g., potassium, magnesium,\
  \ calcium, etc.). This prevents the skill from firing on unrelated ordering tasks\
  \ (such as referrals) or on queries that do not involve labs (e.g., age look\u2011\
  ups). The core ordering logic remains unchanged."
name: low_lab_value_order
provenance:
  action: MODIFY
  epoch: 4
  fixes: 14
  parent_version: 2
  probe_score: 6
  regressions: 3
  triggering_sample_ids:
  - task8_23
  - task8_5
  - task1_7
  - task9_14
  - task10_21
  - task9_20
  - task10_16
  - task8_29
  - task8_15
  - task1_6
  update_cycle: 0
tags: []
version: 3
---

## Low Lab Value Order and Follow‑up Generation (Guarded)

### Guard Clause (must be satisfied before any GET/POST actions)
The skill should **only** run when **all** of the following conditions are true in the task description (case‑insensitive):
1. The text contains the word **"low"** (or a synonym such as "below", "decreased").
2. The text contains the word **"order"** (or "place", "request").
3. The text mentions a **supported laboratory** by name or code. Supported labs are:
   - potassium ("potassium", "K", "serum potassium", LOINC 2823‑3)
   - magnesium ("magnesium", "MG", "serum magnesium", LOINC 19123‑9)
   - calcium ("calcium", "CA", "serum calcium", LOINC 17861‑6)
   - (add additional labs here as needed)
If any of these three checks fail, the skill must **take no action** (i.e., it should not issue a GET, POST, or FINISH). This guard prevents the skill from interfering with unrelated tasks such as referrals or demographic queries.

### Pattern 1: Extract and evaluate the lab value (unchanged)
1. `GET /Observation?code=<LAB_CODE>&patient={{PATIENT_ID}}`
2. Read `entry[0].resource.valueQuantity.value` as a number.
3. Compare to the low‑threshold for the identified lab:
   - Potassium (mmol/L): low if `< 3.5`
   - Magnesium (mg/dL): low if `< 1.5`
   - Calcium (mg/dL): low if `< 8.5`
   - *(extend thresholds as needed)*

### Pattern 2: Create replacement order when low (unchanged)
If the value is low, construct a `ServiceRequest` JSON using the replacement medication code supplied in the task context and `POST /ServiceRequest` **before** calling `FINISH`.

### Pattern 3: Create follow‑up lab order when requested (unchanged)
If the task also asks for a repeat lab, build a second `ServiceRequest` for the appropriate LOINC code and `POST` it before `FINISH`.

### Pattern 4: Finish with the numeric answer (unchanged)
After all required POSTs succeed, call `FINISH([{{VALUE}}])` (or include a timestamp if requested).

### Summary of Changes
- Added a **three‑condition guard** that must be satisfied before any of the original low‑lab ordering logic runs.
- No changes to the actual GET/POST/FINISH sequences; they remain exactly as previously defined.
- This guard ensures the skill does not trigger on unrelated ordering tasks (e.g., orthopedic referrals) or on non‑lab queries (e.g., patient age), thereby fixing the regressions while preserving the original functionality.
