# MedAgentBench-v2

FHIR medical records benchmark (v2, 10 redesigned clinical task types). Tasks are qualitatively harder than v1: multi-step decision trees, time-window reasoning, coordinated writes across multiple FHIR resource types, and safety protocols. Uses the same FHIR Docker image as MedAgentBench — no additional data loading needed.

## Setup

Reuse the MedAgentBench conda environment:

```bash
conda activate medagentbench
pip install -r requirements.txt   # installs any v2-specific additions
```

Pull and start the FHIR server (shared image, same port as MedAgentBench):

```bash
docker pull jyxsu6/medagentbench:latest
docker tag jyxsu6/medagentbench:latest medagentbench
docker run -p 8080:8080 medagentbench
```

The reference solution (`new_refsol.py`) is bundled in `src/server/tasks/medagentbench/` — no separate download required.

Generate data splits (one-time, splits are already included but can be regenerated):

```bash
python data/medagentbench/split_dataset.py
```

## Environment variables

The model backend is chosen at run time with `--agent <preset>`; each preset
reads its credentials/endpoint from environment variables. See
[configs/agents/README.md](configs/agents/README.md) for the full list. For example:

```bash
# gptoss / deepseek / local — self-hosted, OpenAI-compatible
export OSS_API_BASE="http://localhost:8000/v1"

# gemini — Vertex AI
export GOOGLE_CLOUD_PROJECT="my-project"; gcloud auth application-default login

# gpt4 — Azure OpenAI
export AZURE_API_KEY="..." AZURE_API_BASE="https://YOUR-RESOURCE.openai.azure.com" AZURE_API_VERSION="2024-12-01-preview"

# gpt5 — Azure OpenAI Responses API
export AZURE_OPENAI_API_KEY="..." AZURE_OPENAI_BASE_URL="https://YOUR-RESOURCE.openai.azure.com/openai/v1/"
```

## Running experiments

MedAgentBench-v2 uses controller port 5070 and worker base port 5071 (different from v1's 5050/5051), so both can run in parallel if needed.

**Terminal 1 — task worker:**

```bash
conda activate medagentbench
python -m src.start_task -a --config configs/start_task.yaml --base-port 5071
```

**Terminal 2 — learning cycle:**

Run all six methods for one model backend with the helper script at the repo root:

```bash
conda activate medagentbench
./run_all.sh gptoss        # or deepseek / gemini / gpt4 / gpt5 / local
```

The backend is selected with `--agent` (or `GRASP_BACKEND`, or a config's
`agent_preset:`); see [configs/agents/README.md](configs/agents/README.md) for
the presets and the environment variables each needs. Any config below can be
run with `--agent <backend>` to override its default model.

Alternatively, run individual methods by hand:

```bash
conda activate medagentbench

# One config per method; choose the model with --agent (gptoss shown).
python -m src.grasp              --config configs/grasp.yaml              --run-name run_001 --agent gptoss
python -m src.memory_cycle       --config configs/memory_cycle.yaml       --run-name run_001 --agent gptoss
python -m src.batch_memory_cycle --config configs/batch_memory_cycle.yaml --run-name run_001 --agent gptoss
python -m src.evo_memory_cycle   --config configs/evo_memory_cycle.yaml   --run-name run_001 --agent gptoss
python -m src.expel_cycle        --config configs/expel_cycle.yaml        --run-name run_001 --agent gptoss
python -m src.skillx_cycle       --config configs/skillx_cycle.yaml       --run-name run_001 --agent gptoss
```

Swap `--agent gptoss` for `deepseek`, `gemini`, `gpt4`, `gpt5`, or `local` to run
another backend; both the executing agent and the skill/memory writer switch together.

**Resuming an interrupted run:**

If a run is interrupted (API timeout, machine restart, etc.), resume it with the same `--run-name` and add `--resume`. Completed epochs and dev batches are skipped automatically.

```bash
python -m src.grasp --config configs/grasp.yaml --run-name run_001 --agent gptoss --resume
```

The `--resume` flag works identically for all six methods.

## Test set evaluation

Test set evaluation runs **automatically** at the end of every cycle using the best-val checkpoint. Both test splits are evaluated. Results are written directly into the run directory:

```
outputs/<method>/<run-name>/
├── test_eval_best/          # OOD test (tasks 5, 7), best-val checkpoint
│   ├── test_runs.jsonl      # per-sample correctness
│   └── test_score.json      # {split, score, n_correct, n_total}
├── test_eval_baseline/      # OOD test, no-skill/no-memory baseline
│   ├── test_runs.jsonl
│   └── test_score.json
├── id_test_eval_best/       # in-dist test, best-val checkpoint
│   ├── test_runs.jsonl
│   └── test_score.json
├── id_test_eval_baseline/   # in-dist test, no-skill/no-memory baseline
│   ├── test_runs.jsonl
│   └── test_score.json
└── test_scores.json         # summary of all four evaluations
```

To run a standalone evaluation manually (e.g. for the base agent or a custom skill directory):

```bash
# Base agent (no learned skills)
python -m src.run_eval --config configs/grasp.yaml --agent gptoss --split test --run-name base_test

# Best skills from a completed run
python -m src.run_eval --config configs/grasp.yaml --agent gptoss --split test \
    --skills-dir outputs/grasp_gptoss/run_001/skills/best --run-name run_001_best_test
```

The task worker must be running for both automatic and manual evaluation.

## Data splits

| Split | Samples | Description |
|---|---|---|
| dev | 96 | Skill learning (12 per in-dist task type — tasks 1–4, 6, 8, 9, 10) |
| val | 80 | Monitoring during training (10 per in-dist task type) |
| id_test | 64 | In-distribution held-out evaluation (8 per in-dist task type) |
| test | 60 | OOD held-out evaluation (tasks 5, 7 — 30 per type) |

## Task types

| Task | Clinical workflow | FHIR resources |
|---|---|---|
| 1 | CT Abd/Pelvis surveillance — order if >12 months old | Procedure (read), ServiceRequest (write) |
| 2 | DVT prophylaxis reconciliation — ensure exactly one heparin order | MedicationRequest (read + write) |
| 3 | Average heart rate over 6h and 12h windows | Observation (read only) |
| 4 | Urinary catheter dwell check — remove order if >48 hours | Procedure + ServiceRequest (read + write) |
| 5 | Renal mass protocol — CT + IR referral if diagnosis present and CT stale | Condition + Procedure + ServiceRequest (read + write) |
| 6 | Thyroid protocol — levothyroxine or repeat labs based on TSH/FT4 branching | Observation (read), MedicationRequest + ServiceRequest (write) |
| 7 | QTc safety — ECG order + discontinue QT-prolonging drug if QTc >500 ms | Observation + MedicationRequest (read + write) |
| 8 | Naloxone coverage — add naloxone if active opioid without naloxone | MedicationRequest (read + write) |
| 9 | Influenza vaccine recall — order if last shot >365 days ago | Procedure (read), ServiceRequest (write) |
| 10 | COVID-19 booster — order if last vaccine >12 months ago | Procedure + MedicationRequest (read + write) |

## Output structure

```
outputs/
└── grasp_gptoss/
    └── run_001/
        ├── run.log
        ├── val_scores.json
        ├── test_eval_best/       # OOD test, best-val checkpoint
        │   ├── test_runs.jsonl
        │   └── test_score.json
        ├── test_eval_baseline/   # OOD test, no-skill baseline
        │   ├── test_runs.jsonl
        │   └── test_score.json
        ├── id_test_eval_best/    # in-dist test, best-val checkpoint
        │   ├── test_runs.jsonl
        │   └── test_score.json
        ├── id_test_eval_baseline/ # in-dist test, no-skill baseline
        │   ├── test_runs.jsonl
        │   └── test_score.json
        ├── test_scores.json      # summary of all four evaluations
        └── skills/
            ├── learned/        # current skill library
            └── best/           # best checkpoint by val score
```
