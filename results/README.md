# Released results

This directory holds the per-seed accuracies and learned artifacts behind every
table in the paper. It is the data half of the *Code and Data Availability*
statement, alongside the method implementations, prompts, and benchmark adapters
in the rest of the repository.

## What is included

For every run we keep only releasable artifacts:

| File / dir | Meaning |
|---|---|
| `val_scores.json` | Per-epoch validation accuracy (`epoch: baseline, 0, 1, …`). `Val*` = max over training epochs. |
| `test_scores.json` | Held-out scores: `id_test_eval_{baseline,best}` (Test) and `test_eval_{baseline,best}` (OOD), at the best-validation checkpoint. |
| `test_score_{baseline,best}.json` | AgentBench (non-medical) test scores: `baseline` = No-skills, `best` = GRASP at the best checkpoint. |
| `epoch_*/val_score.json` | Validation score at that epoch (feeds the learning-curve figure). |
| `epoch_*/failure_taxonomy.json` | GRASP's failure clustering for that batch (GRASP runs only). |
| `{id_test,test}_eval_{baseline,best}/test_score.json` | The split-level score behind each cell. |
| `baseline/val_score.json` | No-skills validation score for that run. |
| `skills/best`, `skills/learned` | The **learned skill library** (GRASP). `best` = best-validation checkpoint, `learned` = end of training; `.history/` keeps prior versions of each skill. |
| `skillx_library*.json`, `memory.json`, `expel_rules.json` | The learned library/rules for the SkillX, memory, and ExpeL comparators. |
| `config.yaml` | The run configuration (decoding, batch/probe/K, splits). API keys, endpoints, and account identifiers are redacted as `<REDACTED>`. |

## What is excluded (and why)

To keep the public mirror small (≈40 MB instead of ≈15 GB), we drop the full
per-episode agent rollout traces (`*.jsonl`), run logs (`*.log`), ExpeL's
multi-MB raw experience store (its distilled `expel_rules.json` is kept), the
per-epoch `*_updates.json` edit logs, and any file larger than 2 MB. Full traces
are available on request.

## Layout

```
results/
  reproduce_tables.py            # recompute Tables 1 & 5 from the files here
  main/                          # Table 1  (main results)
    <model>/<benchmark>/<method>/run_00N/
  ablations/                     # Table 4  (gpt-oss-120b, MedAgentBench)
    <variant>/run_00N/
  transfer/
    cross_benchmark/<benchmark>/<eval_dir>/   # Table 3  (gpt-oss-120b)
    cross_model/<executor>-executor/...       # Table 2  (Gemini / GPT-5.4 executors)
    cross_writer/...                           # App. cross-writer transfer
    libraries/MedAgentBench/<source>/          # frozen libraries applied at inference
  nonmedical/<env>/run_00N/      # Table 5  (gpt-oss-120b, AgentBench)
  sensitivity/<sweep>/           # App. B/N/K/λ sensitivity sweeps + summary
```

`<model>` ∈ `gpt-oss-120b`, `deepseek-v4-flash`, `gemini-3.1-flash-lite`,
`gpt-4.1`, `gpt-5.4-low`.
`<benchmark>` ∈ `MedAgentBench`, `MedAgentBench-v2`, `FHIR-AgentBench`.
`<method>` ∈ `memory_cycle` (Seq. Memory), `batch_memory_cycle`, `expel_cycle`,
`evo_memory_cycle`, `skillx_cycle`, `skill_cycle` (**GRASP**).
`<env>` ∈ `alfworld`, `webshop`, `dbbench`, `os` (OS Interaction).
The **No-skills** row of each table is the `*_baseline` score pooled across that
model/benchmark's runs.

## Table → directory map

| Table | Source |
|---|---|
| **1** Main results | `main/<model>/<benchmark>/<method>/` (gpt-oss & DeepSeek: 5 seeds; Gemini, GPT-4.1, GPT-5.4: 3 seeds) |
| **2** Cross-model transfer | diagonal = `main/.../skill_cycle`; gpt-oss executor = `transfer/cross_benchmark/MedAgentBench/{gemini,gpt5}_*`; Gemini & GPT-5.4 executors = `transfer/cross_model/{gemini,gpt54}-executor/` |
| **3** Cross-benchmark transfer | `transfer/cross_benchmark/<target-benchmark>/<source>-…-test/`; diagonal = `main/gpt-oss-120b/.../skill_cycle` |
| **4** Ablations | `ablations/<variant>/` — gate-preserving variants (`no_cluster`, `no_reggate`, `fixes_only`, `append_only`) from the 5-epoch budget; `no_gate_k4`, `no_gate_k1` from the default budget. `blind_*` are extra rebuttal variants. |
| **5** Non-medical | `nonmedical/<env>/` — `No skills` = `test_score_baseline.json`, `GRASP` = `test_score_best.json`. ALFWorld uses the 5-epoch budget. |
| App. sensitivity | `sensitivity/` (`b24/b96`, `n16/n72`, `k1/k8`, `lam1/lam4`, plus `summary.csv`) |
| App. cross-writer | `transfer/cross_writer/gpt54-to-oss-<method>-seed*/` |

Frozen libraries actually applied at inference are under
`transfer/libraries/MedAgentBench/<source>/` (`oss-00N`, `gemini-00N`, etc.).

## Reproducing the numbers

```bash
python results/reproduce_tables.py                 # all models (Table 1) + Table 5
python results/reproduce_tables.py gpt-oss-120b    # one model
```
