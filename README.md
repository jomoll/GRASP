<div align="center">

<img src="https://raw.githubusercontent.com/jomoll/GRASP/main/assets/grasp_banner.png" alt="GRASP — Gated Regression-Aware Skill Proposer" width="100%">

<!--- BADGES: START --->
[![arXiv](https://img.shields.io/badge/arXiv-2605.29668-b31b1b.svg?logo=arxiv&logoColor=white)](https://arxiv.org/abs/2605.29668)
[![Project Page](https://img.shields.io/badge/🌐_Project-Page-blue)](https://jomoll.github.io/grasp/)
[![PyPI](https://img.shields.io/pypi/v/grasp-skills?label=grasp-skills&color=00B7EB&logo=pypi&logoColor=white)](https://pypi.org/project/grasp-skills/)
[![Python version](https://img.shields.io/badge/python-3.9+-important?logo=python&logoColor=important)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
<!--- BADGES: END --->

</div>

**GRASP** (Gated Regression-Aware Skill Proposer) learns a small,
**regression-gated skill library** from an agent's own
failure traces: a proposed skill is kept only when it demonstrably improves
performance on a held-out probe set, so the library grows by keeping what helps
and discarding what doesn't. This repository serves two use cases:

1. **A reusable method + framework** (`grasp/`): apply GRASP to *your own* agent
   and tasks through a small `Task` interface, and benchmark *your own*
   self-improvement method against GRASP and five baselines through a `Method`
   interface.
2. **The full paper artifact**: four benchmark families (`benchmarks/`) and all
   released results behind the paper (`results/`), kept verbatim for
   reproduction.

## Table of Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Use GRASP on your own task](#use-grasp-on-your-own-task)
- [Benchmark your own method](#benchmark-your-own-method)
- [How GRASP works](#how-grasp-works)
- [Methods and backends](#methods-and-backends)
- [Benchmarks](#benchmarks)
- [Released results](#released-results)
- [Documentation](#documentation)
- [Repository layout](#repository-layout)
- [Citation](#citation)
- [Contributing](#contributing)
- [License](#license)

## Installation

```bash
pip install grasp-skills          # from PyPI; import as `grasp`
```

Or from source (for the benchmarks, quickstart, and released results):

```bash
git clone https://github.com/jomoll/GRASP.git && cd GRASP
pip install -e .                  # core depends only on PyYAML
```

> The PyPI package ships the reusable core only (`grasp`, `grasp.agents`,
> `grasp.skills`). The benchmarks, quickstart, and results live in the repo.

## Quickstart

Watch GRASP learn one useful skill on a laptop in minutes — **no Docker, no
live FHIR server**. The quickstart runs GRASP on a single MedAgentBench task
(*most recent magnesium within the last 24 hours*) served by an in-process mock.

```bash
# point the 'local' backend at any OpenAI-compatible endpoint
export OPENAI_BASE_URL="http://localhost:8000/v1"
export OPENAI_API_KEY="EMPTY"
export GRASP_MODEL="your-model-name"

python -m examples.quickstart.run --agent local
```

It writes a val-accuracy learning curve and the learned skill library under
`examples/quickstart/runs/`. As GRASP accepts skills that pass its regression
gate, val accuracy rises above the no-skills baseline. See
[`examples/quickstart/`](examples/quickstart) for details and to use it as a
template.

## Use GRASP on your own task

Implement a [`Task`](grasp/task.py) — how to sample, run, and score your
environment — and run GRASP on it:

```python
from grasp import Task, Rollout, run_grasp

class MyTask(Task):
    def samples(self, split):            # "dev" | "val" | "test"
        ...
    def rollout(self, sample, agent):    # run one episode; agent.inference(history)
        ...
        return Rollout(history=..., agent_actions=..., answer=..., status="completed")
    def evaluate(self, sample, rollout): # -> bool
        ...

run_grasp(MyTask(), "config.yaml", agent="local")
```

Optional `Task` hooks (`failure_tags`, `protocol_hook`, `updater_*`) add
environment-specific detail without touching the core. Full guide:
[`docs/add_a_task.md`](docs/add_a_task.md).

## Benchmark your own method

GRASP is the reference [`Method`](grasp/method.py); subclass it to run *your*
self-improvement method on the same tasks, apples-to-apples with GRASP and the
five baselines:

```python
from grasp import Method, run_method

class MyMethod(Method):
    def run(self):                       # self.config, self.run_dir, self.task
        ...

run_method(MyMethod, MyTask(), "config.yaml", agent="local")
```

Guide and worked references (the five baselines):
[`docs/add_a_method.md`](docs/add_a_method.md).

## How GRASP works

Per epoch, over the dev split:

1. **Rollout** the skill-aware agent on each sample and **score** it.
2. **Propose** `K` candidate skill edits (ADD / MODIFY / REMOVE) from the
   failing traces, grouped by failure mode.
3. **Gate**: for each candidate, fork the library, apply it, and re-run a
   balanced, out-of-sample **probe set**; keep the best candidate **only if** it
   nets more fixes than regressions versus the current library — otherwise apply
   nothing.
4. **Monitor** on val (no learning from val); snapshot the best-val library.

This regression gate is what keeps the library small and monotonically useful.
Full description — probe construction, contrastive revision, collapse recovery,
skill injection, and the skill file format — in
[`docs/method.md`](docs/method.md).

## Methods and backends

The paper compares GRASP against a no-skills baseline and five self-improvement
methods, all implemented in each benchmark directory:

| Code | Paper name |
|---|---|
| `grasp` | **GRASP** (ours) — regression-gated skill library |
| `memory_cycle` | Sequential memory |
| `batch_memory_cycle` | Batch memory |
| `expel_cycle` | ExpeL |
| `evo_memory_cycle` | Evo-MedAgent |
| `skillx_cycle` | SkillX |

The executing agent and skill-writer use the same model. Backends are selected
at run time (CLI `--agent` > `GRASP_BACKEND` env > config `agent_preset`); no
secrets are stored in the repo — presets read endpoints and keys from
environment variables.

| Preset | Model (paper) | Provider |
|---|---|---|
| `gptoss` | gpt-oss-120b | self-hosted, OpenAI-compatible |
| `deepseek` | DeepSeek V4 Flash | self-hosted, OpenAI-compatible |
| `gemini` | Gemini 3.1 Flash Lite | Google Vertex AI |
| `gpt5` | GPT-5.4 (low) | Azure OpenAI (Responses API) |
| `gpt4` | GPT-4.1 | Azure OpenAI |
| `local` | any | generic OpenAI-compatible endpoint |

## Benchmarks

Each benchmark is self-contained under `benchmarks/`, with its own README for
environment setup (conda, Docker, data) and a `run_all.sh <backend> [run_name]`
helper.

| Directory | Benchmark | Role in paper | Setup |
|---|---|---|---|
| [`benchmarks/MedAgentBench/`](benchmarks/MedAgentBench) | FHIR reads/writes against a live FHIR server | primary (clinical) | Docker |
| [`benchmarks/MedAgentBench-v2/`](benchmarks/MedAgentBench-v2) | Harder FHIR tasks: multi-step decisions, coordinated writes | primary (clinical) | Docker |
| [`benchmarks/FHIR-AgentBench/`](benchmarks/FHIR-AgentBench) | Structured clinical QA / tool use on an independent FHIR store | supporting (clinical) | GCP Healthcare API |
| [`benchmarks/AgentBench/`](benchmarks/AgentBench) | Four non-clinical environments: OS, DBBench, WebShop, ALFWorld | supporting (generality) | Docker |

## Released results

All numbers behind the paper live under [`results/`](results/) — per-seed
validation, test, and OOD accuracies for every cell of Tables 1–5, the learned
skill libraries, the frozen transfer libraries, and the run configurations.
Reproduce the headline tables directly:

```bash
python results/reproduce_tables.py                 # Table 1 (all models) + Table 5
python results/reproduce_tables.py gpt-oss-120b     # one model
```

See [`results/README.md`](results/README.md) for the full directory↔cell map.

## Documentation

| Page | Contents |
|---|---|
| [docs/method.md](docs/method.md) | How GRASP works — the loop and the regression gate |
| [docs/add_a_task.md](docs/add_a_task.md) | Plug in your own environment via the `Task` interface |
| [docs/add_a_method.md](docs/add_a_method.md) | Benchmark your own method vs. GRASP + 5 baselines |

## Repository layout

```
grasp/                 reusable core (Task/Method API, the GRASP loop, agents)
examples/quickstart/   in-process FHIR demo — no Docker, no server
docs/                  method + how-to guides
benchmarks/            the four paper benchmarks (vendored, verbatim)
results/               released per-seed numbers, skill libraries, reproduce script
```

## Citation

If you use GRASP, please cite the paper (see [`CITATION.cff`](CITATION.cff)).

```bibtex
@article{moll2026grasp,
  title  = {GRASP: Gated Regression-Aware Skill Proposer for Self-Improving LLM Agents},
  author = {Moll, Johannes and Corbeil, Jean-Philippe and Pan, Jiazhen and Hadamitzky, Martin and Rueckert, Daniel and Adams, Lisa and Bressem, Keno},
  journal={arXiv preprint arXiv:2605.29668},
  year={2026}
}
```

## Contributing

Contributions are welcome — new tasks, new method baselines, reference agents,
and docs. See [`CONTRIBUTING.md`](CONTRIBUTING.md). The core stays
benchmark-agnostic (anything environment-specific belongs behind a `Task` hook);
the `benchmarks/` stay faithful to the paper.

## Acknowledgements

GRASP builds on three external benchmarks:

- **[MedAgentBench](https://github.com/stanfordmlgroup/MedAgentBench)** — the clinical FHIR task suite that `benchmarks/MedAgentBench` and the quickstart are based on.
- **[FHIR-AgentBench](https://github.com/glee4810/FHIR-AgentBench)** — the FHIR environment and graders vendored under `benchmarks/FHIR-AgentBench/`.
- **[AgentBench](https://github.com/THUDM/AgentBench)** — the multi-environment agent benchmark vendored under `benchmarks/AgentBench/`.

We are grateful to the authors of these projects for releasing their work openly. If you use GRASP with any of these benchmarks, please include the original citations for the respective benchmark.

## License

MIT (see [`LICENSE`](LICENSE)) for the GRASP core, examples, and docs. Vendored
benchmark code under `benchmarks/AgentBench/` and `benchmarks/FHIR-AgentBench/`
retains its own upstream license.
