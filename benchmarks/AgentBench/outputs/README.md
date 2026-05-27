# AgentBench outputs

Per-seed GRASP runs and their learned skill libraries are released here, one
directory per environment and run:

```
outputs/
  grasp_<task>/                 # task in {os, dbbench, webshop, alfworld}
    run_001/                    # one run; trailing integer = seed (run_00N -> seed N)
      config.yaml               # resolved run config (backend stored as preset name, no secrets)
      val_scores.json           # validation accuracy per epoch (learning curve)
      test_scores.json          # summary of the test evaluation(s)
      test_eval_best/           # test split, best-validation skill checkpoint
      test_eval_baseline/       # test split, no-skills baseline
      skills/                   # learned skill library (best-validation checkpoint)
      epoch_*/                  # (optional) per-epoch dev/val traces
      run.log                   # (optional) full training log
```

The four environments are reported in the paper on the `gptoss` backend across
three seeds (`run_001`, `run_002`, `run_003`); see Table "non-clinical
environments". Each run's `config.yaml` records the backend as a preset **name**
(`agent_preset:`), never expanded endpoints or keys — the agent is re-resolved
from environment variables at evaluation time.

To regenerate a cell from scratch:

```bash
# start the task worker for <task> (see ../README.md), then:
python -m src.grasp --config configs/grasp_<task>.yaml --run-name run_001 --agent gptoss
```
