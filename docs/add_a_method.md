# Benchmark your own self-improvement method

GRASP is one point in a space of methods that improve an agent from its own
experience. The core lets you drop in **your own** method and run it on the same
tasks GRASP uses, so comparisons are apples-to-apples.

A method is a subclass of [`grasp.Method`](../grasp/method.py). The harness
constructs it with a resolved config, a run directory to write into, and the
[`Task`](../grasp/task.py) to learn on, then calls `run()` once.

## The contract

```python
from grasp import Method

class MyMethod(Method):
    # self.config: dict   self.run_dir: Path   self.task: Task
    def run(self) -> None:
        dev = self.task.samples("dev")
        val = self.task.samples("val")

        for epoch in range(self.config["cycle"]["epochs"]):
            for sample in dev:
                rollout = self.task.rollout(sample, self._agent())
                correct = self.task.evaluate(sample, rollout)
                # ... update your memory / skills / prompt from failures ...

            # monitor on val (do not learn from it)
            score = sum(self.task.evaluate(s, self.task.rollout(s, self._agent()))
                        for s in val) / len(val)
            # ... write artifacts into self.run_dir ...
```

You build the executing agent from the resolved backend block with
`grasp.agent.build_agent(self.config["agent"])`, and — if your method injects
learned context — wrap it the way GRASP wraps its agent in
[`grasp/cycle.py`](../grasp/cycle.py).

### Conventional outputs

Not enforced, but writing these makes your runs comparable to GRASP's with the
same tooling:

- `val_scores.json` — a list of `{epoch, score, ...}` (the learning curve)
- per-epoch logs of what the method did
- the learned artifact (skill/memory library) under `run_dir/`

## Running it

```python
from grasp import run_method
run_method(MyMethod, MyTask(), "path/to/config.yaml", agent="local")
```

`run_method` loads the config, resolves the backend (CLI `agent` >
`GRASP_BACKEND` env > config `agent_preset`), creates the run directory, and
calls `MyMethod(config, run_dir, task).run()`.

## Worked references: the five baselines

The paper implements five self-improvement baselines alongside GRASP, in every
benchmark directory. They predate this `Method` base class but follow the same
`__init__(config, run_dir, …)` + `run()` shape, so they are the best concrete
templates to read and diff against:

| Code | Paper name | Idea |
|---|---|---|
| `grasp` | **GRASP** (ours) | regression-gated skill library |
| `memory_cycle` | Sequential memory | append lessons after each sample |
| `batch_memory_cycle` | Batch memory | summarize a batch into memory |
| `expel_cycle` | ExpeL | insight extraction from successes/failures |
| `evo_memory_cycle` | Evo-MedAgent | evolutionary memory updates |
| `skillx_cycle` | SkillX | skill extraction baseline |

See e.g. [`benchmarks/MedAgentBench/src/`](../benchmarks/MedAgentBench/src) —
each `*_cycle.py` entry point plus its `memory/`, `expel/`, `evo_memory/`,
`skillx/` package. To benchmark a new method against these, implement
`Method.run()` and run it on the same `Task` and config.
