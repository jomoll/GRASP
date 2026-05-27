#!/usr/bin/env python3
"""
Recompute paper numbers directly from the released tree, so anyone can confirm the
released per-seed scores reproduce the paper:

* Table 1 (Val* / Test / OOD) from ``results/main/``
* Table 5 (non-medical AgentBench) from ``results/nonmedical/``

Usage:
    python results/reproduce_tables.py            # all models + Table 5
    python results/reproduce_tables.py gpt-oss-120b
"""

import json
import math
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main"
NONMED = HERE / "nonmedical"

MODELS = [
    "gpt-oss-120b",
    "deepseek-v4-flash",
    "gemini-3.1-flash-lite",
    "gpt-4.1",
    "gpt-5.4-low",
]
METHODS = [
    ("Seq. Memory", "memory_cycle"),
    ("Batch Memory", "batch_memory_cycle"),
    ("ExpeL", "expel_cycle"),
    ("Evo-MedAgent", "evo_memory_cycle"),
    ("SkillX", "skillx_cycle"),
    ("GRASP", "skill_cycle"),
]
BENCHES = ["MedAgentBench", "MedAgentBench-v2", "FHIR-AgentBench"]
NONMED_ENVS = ["alfworld", "webshop", "dbbench", "os"]


def load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def std(v):
    v = [x for x in v if x is not None]
    if len(v) < 2:
        return None
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def mab_run(run: Path):
    test = load(run / "test_scores.json")
    val = load(run / "val_scores.json")
    if not test or not val or "id_test_eval_baseline" not in test:
        return None
    epoch_vals = [e["score"] for e in val if e["epoch"] not in ("baseline", -1)]

    def s(key, fb=None):
        e = test.get(key) or (test.get(fb) if fb else None)
        return e["score"] if e else None

    return {
        "val": max(epoch_vals) if epoch_vals else None,
        "test": s("id_test_eval_best", "id_test_eval_baseline"),
        "ood": s("test_eval_best", "test_eval_baseline"),
        "base_val": next((e["score"] for e in val if e["epoch"] in ("baseline", -1)), None),
        "base_test": s("id_test_eval_baseline"),
        "base_ood": s("test_eval_baseline"),
    }


def fhir_run(run: Path):
    best = load(run / "id_test_eval_best" / "test_score.json")
    val = load(run / "val_scores.json")
    if not best or not val:
        return None
    epoch_vals = [e["score"] for e in val if e["epoch"] not in ("baseline", -1)]
    base = load(run / "id_test_eval_baseline" / "test_score.json")
    return {
        "val": max(epoch_vals) if epoch_vals else None,
        "test": best["score"],
        "ood": None,
        "base_val": next((e["score"] for e in val if e["epoch"] in ("baseline", -1)), None),
        "base_test": base["score"] if base else None,
        "base_ood": None,
    }


def collect(model: str, bench: str, method: str):
    d = MAIN / model / bench / method
    if not d.exists():
        return []
    fn = fhir_run if bench == "FHIR-AgentBench" else mab_run
    out = []
    for run in sorted(d.glob("run_*")):
        r = fn(run)
        if r:
            out.append(r)
    return out


def fmt(vals):
    m, s = mean(vals), std(vals)
    if m is None:
        return "  --  "
    return f"{m*100:4.1f}" + (f"±{s*100:.1f}" if s is not None else "")


def main_table(models):
    for model in models:
        print(f"\n=== {model} (Table 1) ===")
        hdr = f"{'Method':<14}"
        for b in BENCHES:
            hdr += f" | {b[:7]:>7} Val/Test/OOD"
        print(hdr)
        for label, key in [("No skills", None)] + METHODS:
            cells = []
            for b in BENCHES:
                if key is None:
                    runs = [r for _, mk in METHODS for r in collect(model, b, mk)]
                    cells.append((fmt([r["base_val"] for r in runs]),
                                  fmt([r["base_test"] for r in runs]),
                                  fmt([r["base_ood"] for r in runs])))
                else:
                    runs = collect(model, b, key)
                    cells.append((fmt([r["val"] for r in runs]),
                                  fmt([r["test"] for r in runs]),
                                  fmt([r["ood"] for r in runs])))
            line = f"{label:<14}"
            for v, t, o in cells:
                line += f" | {v:>10}/{t}/{o}"
            print(line)


def nonmedical_table():
    if not NONMED.exists():
        return
    print("\n=== Non-medical AgentBench, gpt-oss-120b (Table 5) ===")
    print(f"{'Env':<10} {'No skills':>10} {'GRASP':>10}")
    for env in NONMED_ENVS:
        d = NONMED / env
        base = [load(r / "test_score_baseline.json") for r in sorted(d.glob("run_*"))]
        best = [load(r / "test_score_best.json") for r in sorted(d.glob("run_*"))]
        print(f"{env:<10} {fmt([x['score'] for x in base if x]):>10} {fmt([x['score'] for x in best if x]):>10}")


def main():
    models = [a for a in sys.argv[1:]] or MODELS
    main_table(models)
    if not sys.argv[1:]:
        nonmedical_table()


if __name__ == "__main__":
    main()
