---
description: "Map lab/electrolyte shorthand to LOINC, fetch the most recent Observation,\
  \ and return **only the raw numeric value** (or the defined sentinel) so downstream\
  \ decision logic can operate on a clean number. This version adds a guard that prevents\
  \ the skill from emitting any human\u2011readable summary strings, which caused\
  \ regressions in tasks that expect a pure numeric payload."
name: observation_lookup_and_value_extraction
provenance:
  action: ADD
  epoch: 0
  fixes: 7
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task5_16
  - task9_1
  - task2_25
  - task10_27
  - task4_7
  - task5_3
  - task4_26
  - task4_27
  - task10_18
  - task9_6
  update_cycle: 1
tags: []
version: 1
---

## Observation Lookup with Shorthand Mapping – Numeric‑Only Output

### Goal
1. Translate any shorthand (e.g., "K", "MG", "HbA1c") to its canonical LOINC code.
2. Retrieve the most recent Observation for the patient within the requested time window.
3. **Return ONLY** `valueQuantity.value` (or `valueString` when the value is truly a string) as a plain number in the `FINISH` payload. No units, no explanatory text.
4. If no suitable Observation is found, return the sentinel `null` (or `-1` when the task explicitly specifies that sentinel).

### When to Trigger
- The task asks for the "most recent", "last", or "latest" level of a lab/electrolyte **and** the subsequent logic depends on a numeric threshold (e.g., *"if low then order"*). 
- The request supplies a short code/name rather than a full LOINC identifier.

### Guard Clause (prevents regression)
```pseudo
if task contains any of the phrases
  ["most recent", "last", "latest", "within", "past"]
  AND contains a numeric decision phrase
  ["if low", "if high", "if below", "if above", "threshold"]
then apply this skill
else skip – let other skills handle the request.
```
This ensures we do **not** produce a textual summary for tasks that merely want a human‑readable statement, avoiding the regression where a string was returned.

### Shorthand → LOINC map (static, extendable)
```json
{
  "K":   "2823-3",
  "MG":  "2509-2",
  "Mg":  "2509-2",
  "HbA1c": "4548-4",
  "GLU": "2345-7",
  "Na":  "2951-2"
}
```
If the supplied code is not in the map, use it verbatim (it may already be a LOINC).

### Step‑by‑step algorithm
1. **Parse task** – extract patient identifier, shorthand code, and optional date window.
2. **Resolve code** using the map above.
3. **Build GET URL**:
   ```
   GET {base}/Observation?code={LOINC}&patient={MRN}&date=ge{window_start}
   ```
   *If no explicit window is given, default to the last 24 h relative to the current timestamp provided in the task.*
4. **Execute GET** – receive a Bundle.
5. **Handle empty bundle**:
   - If `total == 0`, `FINISH([null])` (or `FINISH([-1])` when the task mentions that sentinel).
6. **Extract value** from the first entry (most recent):
   - If `valueQuantity` exists → `value = valueQuantity.value` (numeric).
   - Else if `valueString` exists → attempt to parse a number from the string; if parsing fails, treat as missing.
7. **Return**:
   ```
   FINISH([value])
   ```
   *Never include units or explanatory text.*

### Fallback & Logging
- Log a warning if extraction fails and return the sentinel.
- The skill does **not** perform any ordering; it only supplies the numeric result for downstream logic.

### Example
**Task:** "Check patient S6192632's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium."
1. Map `MG` → `2509-2`.
2. GET `/Observation?code=2509-2&patient=S6192632&date=ge2023-11-12T10:15:00Z`.
3. Bundle contains `valueQuantity.value = 2.3`.
4. Skill outputs `FINISH([2.3])`.
5. Downstream decision logic sees `2.3` (normal) and does not place an order.

### Success Indicators
- URL uses a LOINC code, not the original shorthand.
- `FINISH` payload is a single numeric element (or the defined sentinel).
- No units or descriptive strings are present.
- Downstream ordering logic receives the numeric value and behaves correctly.

### Failure Indicators
- URL still contains the original shorthand.
- `FINISH` contains a string, array with units, or any extra text.
- Sentinel is returned when a valid numeric value exists.

---
*This revised skill keeps the core mapping and extraction mechanism but adds a precise guard clause and enforces a numeric‑only return, eliminating the regression where a textual summary was emitted.*
