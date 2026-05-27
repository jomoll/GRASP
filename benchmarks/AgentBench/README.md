# GRASP on AgentBench

Code and instructions to reproduce the four non-clinical AgentBench environments
reported in the paper — **OS Interaction**, **DBBench**, **WebShop**, and
**ALFWorld** — with GRASP (the skill-learning cycle). These provide supporting
evidence of generality beyond the clinical FHIR benchmarks.

GRASP trains a skill library over a dev split, checkpoints on a validation
split, and evaluates the best-validation checkpoint and a no-skills baseline on
a held-out test split. In the paper these environments use the `gptoss`
(gpt-oss-120b) backend across three seeds; any backend below can be used.

> Built on [AgentBench](https://github.com/THUDM/AgentBench) (Liu et al., 2024).
> The original project README is preserved as [README.upstream.md](README.upstream.md);
> license in [LICENSE](LICENSE).

| Code term | Paper term |
|---|---|
| `grasp` (`src/grasp.py`, `configs/grasp_*.yaml`) | GRASP (ours) |
| no-skills baseline (`run_baseline: true`) | No skills |

The five memory baselines (Sequential, Batch, ExpeL, Evo, SkillX) are evaluated
on the clinical benchmarks only; see the `MedAgentBench*/` directories.

## Prerequisites

- Python 3.9
- Docker (task environments run in containers)
- A model backend — see [configs/agents/README.md](configs/agents/README.md)
  for presets (`gptoss`, `deepseek`, `gemini`, `gpt4`, `gpt5`, `local`) and the
  environment variables each requires. No keys or endpoints are stored in the repo.

```bash
pip install -r requirements.txt
```

## Data

Dev/val/test splits are committed under `data/<task>/split_*.json` (regenerate
with `python data/<task>/split_dataset.py`). DBBench and OS Interaction bundle
their task data directly. WebShop and ALFWorld load large external environments
inside their Docker images:

- **DBBench**: `docker pull mysql:8`
- **OS Interaction**: build the images in `data/os_interaction/res/dockerfiles/`
  (`default`, `packages`, `ubuntu`) — see [README.upstream.md](README.upstream.md).
- **WebShop**: `docker pull longinyu/agentbench-webshop` (~16 GB RAM to run).
- **ALFWorld**: pulls its game files on first run.

## Starting task workers

Each environment runs as a controller + task worker. Start the worker for the
task you want (each on its own controller port), then run GRASP in another
terminal.

```bash
# OS Interaction (controller :5040)
python -m src.start_task -a --config configs/start_skill_task_os.yaml       --controller-port 5040 --base-port 5041
# DBBench (controller :5010)
python -m src.start_task -a --config configs/start_skill_task_dbbench.yaml  --controller-port 5010 --base-port 5011
# WebShop (controller :5090)
python -m src.start_task -a --config configs/start_skill_task_webshop.yaml  --controller-port 5090 --base-port 5091
# ALFWorld (controller :5060)
python -m src.start_task -a --config configs/start_skill_task_alfworld.yaml --controller-port 5060 --base-port 5061
```

To self-host model weights inside the worker container, set
`AGENTBENCH_MODELS_DIR=/path/to/models` before starting it (otherwise omitted).

## Running GRASP

Select the backend with `--agent` (or `GRASP_BACKEND`, or the config's
`agent_preset:`). Example with the paper's `gptoss` backend:

```bash
export OSS_API_BASE="http://localhost:8000/v1"   # your gpt-oss-120b endpoint

python -m src.grasp --config configs/grasp_os.yaml      --run-name run_001 --agent gptoss
python -m src.grasp --config configs/grasp_dbbench.yaml --run-name run_001 --agent gptoss
python -m src.grasp --config configs/grasp_webshop.yaml --run-name run_001 --agent gptoss
python -m src.grasp --config configs/grasp_alfworld.yaml --run-name run_001 --agent gptoss
```

The trailing integer of `--run-name` is forwarded as the seed by `run_all.sh`.

### All four tasks, multiple seeds

```bash
./run_all.sh gptoss run_001    # workers must be running first
./run_all.sh gptoss run_002
./run_all.sh gptoss run_003
```

### Other backends

```bash
GRASP_BACKEND=gemini python -m src.grasp --config configs/grasp_os.yaml --run-name run_001
./run_all.sh local run_001     # any OpenAI-compatible endpoint via LOCAL_API_BASE/LOCAL_MODEL
```

## Test evaluation

`run_baseline: true` makes each run evaluate the no-skills baseline automatically.
To re-evaluate a finished run on the test split:

```bash
python -m src.eval_test --run outputs/grasp_os/run_001 --skills best     --controller-address http://localhost:5040/api
python -m src.eval_test --run outputs/grasp_os/run_001 --skills baseline --controller-address http://localhost:5040/api
```

## Outputs

Per-seed results and learned skill libraries are written under `outputs/` — see
[outputs/README.md](outputs/README.md) for the directory layout and what is
released with the paper.
