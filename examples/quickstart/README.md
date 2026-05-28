# GRASP quickstart — magnesium 24h (no Docker, no server)

Watch GRASP learn **one** useful skill on a laptop in minutes. The quickstart
runs GRASP on a single MedAgentBench task family — **task4: most recent
magnesium within the last 24 hours** — served by an in-process mock FHIR store
(no Docker, no live FHIR server, no clinical data).

## What it does

The agent answers the same question for 12 patients:

> *What is the most recent magnesium level of patient `<MRN>` within the last 24 hours?*
>
> *The answer should be a single number in mg/dL, or `-1` if no measurement
> within the last 24 hours is available.*

By design, **half** the patients have a magnesium reading within 24 h (real
numeric answer) and **half** do not (answer `-1` — either no MG observations at
all, or only readings older than 24 h). Splits: **8 dev / 4 val**, balanced.

The behaviour GRASP needs to learn — which it discovers from the agent's own
failures, **without anything hand-written here** — is the one captured by the
released MedAgentBench skill called `observation_value_extraction`:

| Behaviour | Correct | Wrong |
|---|---|---|
| Extract the numeric value | `valueQuantity.value` as a number | the formatted string with units |
| Apply the 24-hour window | filter by `effectiveDateTime >= now − 24h` | most-recent overall |
| Sentinel when none | `FINISH([-1])` | `FINISH([])`, `"no data"`, etc. |
| Format | `FINISH([2.1])` | `FINISH(["2.1 mg/dL"])`, prose |

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
accepts a skill that passes its regression gate.

## How it's wired (use it as a template)

- [`mock_fhir.py`](mock_fhir.py) — in-process FHIR search (Patient / Observation)
- [`data.py`](data.py) — canned patients, magnesium observations, and the dev/val samples
- [`task.py`](task.py) — a `grasp.Task`: the rollout protocol loop and the
  task4 grader, plus optional `failure_tags` / `updater_*` hooks
- [`run.py`](run.py) — ties the task to `grasp.run_grasp`

To learn GRASP on your own environment, copy `task.py` and implement
`samples` / `rollout` / `evaluate` for it. See [`docs/add_a_task.md`](../../docs/add_a_task.md).
