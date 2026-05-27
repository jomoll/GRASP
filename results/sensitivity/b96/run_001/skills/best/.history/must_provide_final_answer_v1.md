---
description: "Require the agent to emit a FINISH response after processing a GET result\
  \ **only for tasks that request a concrete data answer and do not involve creating\
  \ or ordering any FHIR resources**. This prevents the agent from stopping after\
  \ reasoning on data\u2011retrieval\u2011only queries while allowing normal POST/PUT\
  \ workflows for ordering, prescribing, scheduling, or referral tasks."
name: must_provide_final_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 12
  probe_score: 16
  regressions: 1
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task5_20
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task3_14
  - task4_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

## Final‑Answer‑After‑GET (Data‑Only Tasks)

### When to Apply
- The user request **asks for a concrete value** (e.g., age, lab result, presence/absence) **and does not contain any ordering/creation verbs** such as `order`, `prescribe`, `schedule`, `create`, `send`, `refer`, `referral`, `request`, `generate`, `add`, `make`, etc.
- You have just received the JSON bundle from a `GET` request.
- No further `POST`/`PUT`/`PATCH` actions are required to satisfy the request.

### What to Do
1. **Parse** the GET response and extract the required field(s).
2. **Apply** any conditional logic (e.g., thresholds, date windows).
3. **Emit** a single `FINISH` line whose payload matches the exact type the task expects (integer, string, or JSON array). **Do not** add extra prose or explanatory text.
4. **Do not** emit `FINISH` before the GET response is processed, and **do not** emit it if the task later requires a POST/PUT.

### Formatting Rules
- For a single integer: `FINISH([45])`
- For a single string: `FINISH(["Patient not found"])`
- For a list of strings/values: `FINISH(["S3213957", "S3213958"])`
- **Never** wrap the answer in additional sentences or markdown.

### Guard Clause (exempt from this rule)
If the original instruction contains any of the following case‑insensitive keywords, the skill **does not apply** and the agent may proceed with POST/PUT actions before finishing:
`order`, `prescribe`, `schedule`, `create`, `send`, `refer`, `referral`, `request`, `generate`, `add`, `make`.

### Failure Indicators
- The turn ends with reasoning text and no `FINISH`.
- `FINISH` appears before the GET response is processed.
- The payload inside `FINISH` does not match the expected type or contains extra prose.
- `FINISH` is emitted for a task that later requires a POST/PUT (e.g., ordering a medication or referral).

### Success Indicators
- After receiving the GET bundle, the agent extracts the needed data, then outputs a correctly formatted `FINISH` line **and nothing else**.
- No POST/PUT actions are performed for the same turn when the guard clause is active.

---
*This revised rule preserves the original intent of forcing a final answer for pure data‑retrieval queries while exempting tasks that involve ordering or creating resources, thereby fixing the regressions observed in task5_16 and task8_7.*
