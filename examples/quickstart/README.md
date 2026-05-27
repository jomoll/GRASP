# GRASP quickstart — FHIR lookup (no Docker, no server)

Watch GRASP learn useful skills on a laptop in minutes. This example runs GRASP
on a self-contained slice of [MedAgentBench](../../benchmarks/MedAgentBench)'s
**read-only FHIR lookup tasks**, served by an in-process mock FHIR store — no
Docker, no live FHIR server, no clinical data.

## What it does

The agent answers clinical lookup questions by issuing FHIR `GET` requests and a
final `FINISH([...])`, across five read-only task families:

| Family | Question | Skill it tends to teach |
|---|---|---|
| `task1` | MRN of a patient by name + DOB | how to build the `Patient` search |
| `task2` | Age of a patient by MRN | read `birthDate`, compute age |
| `task4` | Most recent magnesium within 24h | `Observation` recency + time window |
| `task6` | Average glucose within 24h | aggregate `valueQuantity.value` |
| `task7` | Most recent glucose | most-recent-by-`effectiveDateTime` |

GRASP discovers these skills **from the agent's own failure traces** — nothing
about them is hand-written. The behaviours mirror the released MedAgentBench
skill libraries (e.g. patient lookup, observation value extraction, formatting
`FINISH` as a bare number rather than a sentence with units).

## Run it

From the repository root:

```bash
pip install -e .

# Point the 'local' backend at any OpenAI-compatible endpoint:
export OPENAI_BASE_URL="http://localhost:8000/v1"   # your endpoint
export OPENAI_API_KEY="EMPTY"                         # or your key
export GRASP_MODEL="your-model-name"

python -m examples.quickstart.run --agent local
```

Useful flags: `--set cycle.epochs=2` (shorten), `--run-name myrun`, `--resume`,
`--force`. See `configs/grasp.yaml` for the loop hyperparameters.

## What you get

Artifacts are written under `examples/quickstart/runs/<run-name>/`:

- `val_scores.json` — the val accuracy learning curve (baseline → each epoch)
- `skills/best/` — the learned skill library at its best-val checkpoint
- `epoch_*/` — per-epoch dev runs, skill-update events, and val runs
- `run.log` — full console log

A successful run shows val accuracy rising above the no-skills baseline as GRASP
accepts skills that pass its regression gate.

## How it's wired (use it as a template)

- [`mock_fhir.py`](mock_fhir.py) — in-process FHIR search (Patient / Observation)
- [`data.py`](data.py) — canned patients, observations, and the dev/val samples
- [`task.py`](task.py) — a `grasp.Task`: the rollout protocol loop and the
  read-only graders, plus optional `failure_tags` / `updater_*` hooks
- [`run.py`](run.py) — ties the task to `grasp.run_grasp`

To learn GRASP on your own environment, copy `task.py` and implement
`samples` / `rollout` / `evaluate` for it. See [`docs/add_a_task.md`](../../docs/add_a_task.md).
