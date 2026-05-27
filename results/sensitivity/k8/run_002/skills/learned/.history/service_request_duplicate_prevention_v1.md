---
description: Prevent posting duplicate ServiceRequest resources for the same patient
  and code. The rule only activates when the agent is *about to* issue a POST /ServiceRequest;
  it does not interfere with tasks that finish after a GET or that decide no order
  is needed.
name: service_request_duplicate_prevention
provenance:
  action: ADD
  epoch: 2
  fixes: 9
  probe_score: 3
  regressions: 4
  triggering_sample_ids:
  - task10_13
  - task9_9
  - task5_19
  - task8_19
  - task5_3
  - task9_27
  - task9_14
  - task5_7
  - task9_3
  - task3_3
  update_cycle: 1
tags: []
version: 1
---

# ServiceRequest Duplicate Prevention

## When to Apply
- **Only** when the agent has decided to create a new `ServiceRequest` and is about to execute `POST /fhir/ServiceRequest`.
- Do **not** run this pattern for any other request type (e.g., `GET /Observation`, `FINISH`, etc.).
- If the clinical logic determines that no order is required, simply `FINISH` – the duplicate‑prevention flow is skipped.

## Core Pattern (unchanged)
1. **Pre‑order existence check** – before the POST, query for an active request with the same patient and exact `code`:
   ```
   GET /fhir/ServiceRequest?patient=Patient/{MRN}&code={system}|{code}&status=active
   ```
2. **Decision**
   - If the returned bundle has `total > 0`, **skip** the POST – a matching active request already exists.
   - If `total == 0` (or the GET fails), proceed to step 3.
3. **Safe POST** – construct and `POST /fhir/ServiceRequest` as required.
4. **Optional local record** – store the new `ServiceRequest.id` for intra‑task de‑duplication.

## Guard Clause (new)
- **Do not** perform the GET‑search if the agent has not generated a POST command in the current reasoning step. This prevents the rule from being invoked on tasks that only need to read data or return a result.
- **Do not** block a legitimate order when the GET query fails for network reasons; in that case, assume no duplicate exists, log a warning, and continue with the POST.

## Example (unchanged)
*The example below still applies when an order is required; it is omitted here for brevity.*

## Success Indicators
- No `POST /ServiceRequest` is sent when an active request with the same `code` and `patient` already exists.
- The agent finishes tasks that do not need an order without performing an unnecessary duplicate‑check GET.
- System logs contain no "duplicate_service_request_posted" warnings.

## Failure Indicators
- A `POST /ServiceRequest` is issued despite a preceding successful GET showing an existing active request.
- The rule runs (issues a GET) on a task that only required a GET Observation or a `FINISH`, causing the agent to deviate from the expected flow.
