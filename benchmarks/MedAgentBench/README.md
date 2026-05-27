# MedAgentBench

FHIR medical records benchmark (v1, 10 clinical task types). Agents read and write FHIR resources against a live FHIR server hosted in Docker.

## Setup

```bash
conda create -n medagentbench python=3.9
conda activate medagentbench
pip install -r requirements.txt
```

Pull and start the FHIR server:
**Terminal 1 — fhir server (keep running for all experiments, only need one for both datasets):**

```bash
docker pull jyxsu6/medagentbench:latest
docker tag jyxsu6/medagentbench:latest medagentbench
docker run -p 8080:8080 medagentbench
```

Wait until the console shows "Started Application in XXX seconds", then verify at `http://localhost:8080/`.

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

Start the task worker in one terminal, then run the learning cycle in another.

**Terminal 2 — task worker (keep running for all experiments):**

```bash
conda activate medagentbench
python -m src.start_task -a --config configs/start_task.yaml
```

**Terminal 3 — learning cycle:**

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
├── test_eval_best/          # OOD test (tasks 6, 7), best-val checkpoint
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
| dev | 96 | Skill learning (12 per in-dist task type — tasks 1–5, 8, 9, 10) |
| val | 80 | Monitoring during training (10 per in-dist task type) |
| id_test | 64 | In-distribution held-out evaluation (8 per in-dist task type) |
| test | 60 | OOD held-out evaluation (tasks 6, 7 — 30 per type) |

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
