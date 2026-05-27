# Add your own task / benchmark

To run GRASP (or any [`Method`](../grasp/method.py)) on a new environment,
implement [`grasp.Task`](../grasp/task.py). It has three required methods and a
few optional hooks.

## The contract

```python
from grasp import Task, Rollout

class MyTask(Task):
    name = "my-task"

    def samples(self, split):            # "dev" | "val" | "test"
        # return a list of dicts; the only required key is a stable "id".
        ...

    def rollout(self, sample, agent):    # run ONE episode
        # drive `agent.inference(history, tools=None)` against your environment,
        # then return a Rollout capturing the transcript and outcome.
        ...
        return Rollout(history=history, agent_actions=actions,
                       answer=final_answer, status="completed", raw=...)

    def evaluate(self, sample, rollout): # -> bool
        ...
```

### `Rollout` fields

The learning loop reads these, so populate what applies:

- `history` — the chat transcript (`{"role", "content"}`; use role `"agent"`
  for the agent's turns).
- `agent_actions` — the agent's actions/tool calls as readable strings (used to
  describe failures to the skill writer).
- `answer` — the final answer text, if the task has one.
- `status` — `"completed"`, or a short status such as `"agent invalid action"` /
  `"task limit reached"` / `"error"` that the gate treats specially.
- `raw` — the native result, for your `evaluate`.

### Optional hooks

- `failure_tags(sample, rollout) -> list[str]` — mechanism tags for failures;
  improves proposal quality.
- `protocol_hook(first_user_content) -> str | None` — inject an
  environment-specific tool reminder alongside skills.
- `updater_task_family` / `updater_guidance` / `updater_failure_examples` —
  domain labels and guidance threaded into the skill-writer prompt.

The smallest complete example is the quickstart:
[`examples/quickstart/task.py`](../examples/quickstart/task.py) (rollout protocol
loop + graders) backed by an in-process mock in
[`mock_fhir.py`](../examples/quickstart/mock_fhir.py). Copy it as a starting point.

## Config a task needs

A run config supplies the backend and the loop hyperparameters; the task itself
provides the data. Minimum:

```yaml
agent_preset: local              # resolved from <config dir>/agents/local.yaml
skills:
  base_dir: path/to/skills/base  # the read-only skeleton template lives here
cycle:
  epochs: 3
  update_every: 100
  grpo_k: 3
  grpo_eval_n: 8
```

## Wiring an AgentBench environment

`benchmarks/AgentBench` ships ten task families; four are wired for the paper
(`os`, `dbbench`, `webshop`, `alfworld`). The other six —
**`avalon`, `card_game`, `kg`, `ltp`, `mind2web`, `task_assembly`** — have task
servers under
[`benchmarks/AgentBench/src/server/tasks/`](../benchmarks/AgentBench/src/server/tasks)
and configs under
[`benchmarks/AgentBench/configs/tasks/`](../benchmarks/AgentBench/configs/tasks),
but no GRASP wiring. Two ways to reach them:

1. **In-process `Task` (recommended for the core).** Write a `Task` whose
   `rollout` drives the environment directly and whose `evaluate` calls that
   environment's grader — exactly what the quickstart does for FHIR. You provide
   `samples` from the task's data split.

2. **Wrap a running AgentBench worker.** AgentBench runs tasks behind a
   client/server worker (`TaskClient.run_sample(index, agent)`). A thin `Task`
   can start or connect to that worker and translate its `TaskClientOutput` into
   a `Rollout` (map `history`, the final answer, and status). This reuses the
   benchmark's existing environment and grader unchanged.

Either way, splits come from `Task.samples()`, so you control train/val/test
without touching the core. Define `failure_tags` for the environment's
characteristic failures and set `updater_task_family` to get sharper proposals.
