---
description: Validate that the final answer matches the expected type/structure inferred
  from the question.
name: answer_format_validation
provenance:
  baseline_fixes: 3
  baseline_regressions: 3
  epoch: 2
  failure_mode: answer_format_wrong_type
  fixes: 6
  probe_score: 6
  regressions: 0
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 0702bc77d929f78085010bb0
  - 074c7225bee20e2006c6db58
  - 09b1b086d491d385b6744dd6
  - 0a43e2fe814473ab9035db70
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should invoke this skill immediately before emitting the final answer for any patient‑data query. Trigger it when the question contains keywords that imply a specific answer shape, such as:
- **Boolean queries** – "Has … been…?", "Was … given?", "Did … receive?" → expect a single "Yes"/"No" (or true/false).
- **Date/Time queries** – "When did …?", "What was the last time…?", "First/last … since …" → expect an ISO‑8601 datetime string.
- **Numeric queries** – "What was the total…", "Give me the amount…", "How many…", "What was the minimum/maximum value…" → expect a plain number (int or float) possibly with units.
- **Count queries** – "How many times…", "Number of … visits" → expect an integer.
- **Mapping queries** – questions that ask about several items in one sentence, e.g., "Has docusate sodium, glucose gel, or heparin been prescribed?" → expect a JSON object where each requested item maps to "Yes"/"No".
If the inferred expectation is not met, the skill must either re‑format the answer or raise a clear error so a higher‑level fallback can retry.

## Procedure
1. **Extract expectation**
   - Scan the original user instruction for the trigger keywords listed above.
   - Set `expected_type` to one of: `boolean`, `datetime`, `numeric`, `integer`, `mapping`.
2. **Inspect the generated answer**
   - If the answer is a Python object, convert it to its JSON representation.
   - For `boolean`: accept only the exact strings `"Yes"`, `"No"` (case‑insensitive) or the booleans `true`/`false`.
   - For `datetime`: verify the string matches the ISO‑8601 pattern `YYYY-MM-DDTHH:MM:SS` (allow optional timezone offset).
   - For `numeric`: ensure the value is a number (int or float) and not wrapped in extra text.
   - For `integer`: ensure the value is an integer and not a float with a decimal part.
   - For `mapping`: ensure the answer is a JSON object (dictionary) where each key is a normalized target name and each value is exactly `"Yes"` or `"No"`.
3. **Re‑format if possible**
   - If the answer contains the correct data but extra wording (e.g., "The answer is: Yes"), strip the surrounding text and keep only the core value.
   - For a list of single‑item dicts (`[{"drug": "Yes"}, {"other": "No"}]`), collapse it into a single mapping object (`{"drug": "Yes", "other": "No"}`).
4. **Validate**
   - If after re‑formatting the answer still does not satisfy the `expected_type`, raise an exception with a message like `"Answer format mismatch: expected <type> but got <actual>"`.
   - The exception will be caught by the orchestrator, which will then retry the query with a clearer prompt or fallback.
5. **Pass through**
   - If the answer passes validation, return it unchanged to the caller.

## Checks
- The original user instruction is available as `question`.
- The candidate answer is available as `answer` (Python object or string).
- Verify the answer type matches the inferred expectation **before** any final rendering to the user.
- For datetime answers, ensure the string can be parsed with `datetime.fromisoformat`.
- For numeric answers, ensure `isinstance(answer, (int, float))` after possible string conversion.
- For mapping answers, ensure `isinstance(answer, dict)` and every value is exactly `"Yes"` or `"No"` (case‑insensitive).

## Avoid
- Assuming the answer is correct without checking; this skill exists precisely to catch format mismatches.
- Over‑generalising to accept any free‑text; only the minimal required representation should be allowed.
- Modifying the semantic content of the answer – only structural re‑formatting is permitted.
- Applying the skill to questions that do not have a clear expected type (e.g., open‑ended narrative requests).
