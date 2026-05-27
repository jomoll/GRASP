---
description: Handle presence, timing, and aggregation of Observation events with clear
  messages when no matching data. Trigger only on queries that explicitly reference
  laboratory, test, measurement, result, value, or output concepts and do not mention
  procedures or surgeries.
name: observation_event_presence_query
provenance:
  baseline_fixes: 8
  baseline_regressions: 5
  epoch: 2
  failure_mode: empty_result_not_handled
  fixes: 11
  probe_score: 7
  regressions: 1
  triggering_sample_ids:
  - 06ba722e2ac0589ffacd1249
  - 0741b96a36302acf8ace5c02
  - 0a43e2fe814473ab9035db70
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must invoke this skill for any question that **directly asks about a lab/test/measurement/observation value** for a patient and may return zero results. Typical trigger phrases include:
- "when was the last *creatinine* test"
- "how many hours since the last *bicarbonate* lab"
- "did patient X have any *output* measurements"
- "total *output* since …"
- "average/minimum/maximum *sodium* value"
- "count of *blood pressure* readings"

**Do NOT invoke** for queries that refer to **Procedure, MedicationRequest, Encounter, or any non‑observation activity** (e.g., "any procedures", "surgeries", "medications").

## Procedure
1. **Retrieve Observations**
   ```json
   {"resource_type": "Observation", "patient_fhir_id": "<patient_fhir_id>"}
   ```
   Use the `get_resources_by_patient_fhir_id` tool.

2. **Optional Encounter Scope**
   If the question mentions a specific encounter type, first fetch relevant `Encounter` resources, build a set of encounter IDs (including child encounters via `partOf`), and later filter observations whose `encounter.reference` is in that set.

3. **Filter by Observation Keywords**
   - Define a whitelist of observation‑related keywords, e.g., `lab, test, measurement, result, value, output, level, count, concentration, pressure, glucose, sodium, creatinine, bicarbonate, culture, microbiology`.
   - Normalize all code display strings, `code.text`, and `code.coding.code` to lower‑case and collapse whitespace.
   - Keep an observation if **any** of its normalized code strings contains **all** keywords from the user query that belong to the whitelist.
   - **Guard clause**: if the query contains any of the excluded terms `procedure, surgery, operation, medication, med, drug`, abort the skill and let another skill handle it.

4. **Apply Date Range (if supplied)**
   Parse explicit dates or month/year from the question and discard observations whose `effectiveDateTime` (or `effectivePeriod.start`) fall outside the range.

5. **Determine Query Type**
   - **Last‑time / First‑time**: sort matching observations by datetime and pick the latest or earliest.
   - **Elapsed time**: compute whole‑hour difference between the current assumed time (or supplied reference) and the datetime of the last matching observation.
   - **Presence**: answer `Yes` if at least one match, otherwise `No`.
   - **Aggregation** (`sum, avg, min, max, count`): extract numeric values from `valueQuantity`, `valueDecimal`, `valueInteger`, or parsable `valueString` and compute the requested statistic.

6. **Generate Answer**
   - If **no matching observations** are found, **never** return a numeric default. Respond with a clear message, e.g.:
     - `No <test> observations found.`
     - `No <test> results in the specified period.`
     - `No data` (for pure numeric aggregation).
   - Otherwise format the result according to the query type:
     - ISO‑8601 datetime for timestamps.
     - Integer/float (preserve unit if all observations share the same unit).
     - `Yes`/`No` for presence.

## Implementation notes
- Use **single quotes** inside the Python code passed to `execute_python_code` to avoid JSON‑string quoting issues.
- Example Python snippet (single‑quoted strings only):
  ```python
  import re, json
  from datetime import datetime
  obs = retrieved_resources.get('Observation', [])
  start = datetime(2023, 1, 1)  # replace with parsed start date if any
  keywords = ['micro', 'culture', 'gram', 'bacterial', 'viral', 'fungal', 'pathogen']
  def contains_keyword(s):
      s = (s or '').lower()
      return any(k in s for k in keywords)
  matches = []
  for o in obs:
      code = o.get('code', {})
      if not any(contains_keyword(c.get('display','')) or contains_keyword(c.get('code','')) for c in code.get('coding', [])):
          continue
      dt_str = o.get('effectiveDateTime') or o.get('effectivePeriod', {}).get('start')
      if not dt_str:
          continue
      try:
          dt = datetime.fromisoformat(dt_str).replace(tzinfo=None)
      except Exception:
          continue
      if dt >= start:
          matches.append(dt)
  if matches:
      answer = max(matches).isoformat()
  else:
      answer = 'No microbiological test observations found since {}.'.format(start.date().isoformat())
  print(answer)
  ```
- Ensure any constructed JSON payloads (e.g., for tool calls) are well‑formed; avoid embedding raw double quotes inside the JSON string.

## Checks
- Confirm the resource type is **Observation** (or **Encounter** for scoping).
- Verify that the encounter filter (if used) yields at least one encounter; otherwise answer `No <encounter type> encounters found.`
- Ensure at least one observation passes all filters before performing calculations.
- Round elapsed‑time answers down to whole hours.
- Preserve unit only when uniform across all matched observations.

## Avoid
- Triggering on non‑Observation queries (Procedures, Medications, etc.).
- Returning `0`, `0.0`, or an empty string when the result set is empty.
- Ignoring date constraints or encounter scope.
- Mixing different test codes that do not share the required keywords.
- Producing non‑ISO‑8601 timestamps when a datetime is expected.
- Embedding unescaped double quotes inside the JSON sent to tools.
