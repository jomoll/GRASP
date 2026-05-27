"""
Run test-set evaluation for a completed GRASP run.

Usage:
    # Evaluate baseline (no learned skills):
    python -m src.eval_test --run outputs/grasp_os/run_001 --skills baseline

    # Evaluate best-val-epoch skills:
    python -m src.eval_test --run outputs/grasp_os/run_001 --skills best

    # Evaluate a specific epoch's skills:
    python -m src.eval_test --run outputs/grasp_os/run_001 --skills epoch_3

Results are written to <run_dir>/test_score_<skills>.json and test_runs_<skills>.jsonl.
"""

import argparse
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml


def _load_json_list(path: Path, label: str):
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"{label} must be a JSON array, got {type(data).__name__}")
    return data


def _score_result(sample, result, eval_fn):
    """Mirrors the scoring logic from skills/cycle.py."""
    if result.error or result.output is None:
        return False
    if result.output.result is None:
        return False
    if isinstance(result.output.result, dict) and "is_correct" in result.output.result:
        return result.output.result.get("is_correct") is True
    if eval_fn is None:
        return False
    try:
        return eval_fn(sample, result.output) is True
    except Exception as e:
        print(f"  [EvalTest] eval error for {sample.get('id')}: {e}")
        return False


def run_test_eval(run_dir: Path, skills_label: str, concurrency: int = 8,
                  controller_address: str = None, agent: str = None) -> dict:
    """
    Evaluate the test split for a run.

    skills_label: "baseline" | "best" | "epoch_N"
    controller_address: optional override for task.controller_address (point the
        eval at a specific task worker/controller, e.g. http://localhost:5200/api).
    agent: optional backend preset override; defaults to the run's agent_preset.
    Returns the score record dict.
    """
    config_path = run_dir / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"No config.yaml found in {run_dir}")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    if controller_address:
        config.setdefault("task", {})["controller_address"] = controller_address
        print(f"  Controller: {controller_address} (overridden)")

    # Derive test split path from val split path
    val_path = Path(config["data"]["val"])
    test_path = Path(str(val_path).replace("_val.", "_test."))
    if not test_path.exists():
        raise FileNotFoundError(f"Test split not found at {test_path} (derived from {val_path})")

    test_data = _load_json_list(test_path, "test split")
    print(f"  Test split: {test_path} ({len(test_data)} samples)")

    # Determine learned_dir for this evaluation
    import importlib
    import shutil

    from src.client.task import TaskClient
    from src.skills.repository import SkillRepository
    from src.typings.general import InstanceFactory
    from src.client.agents.skill_aware_agent import SkillAwareAgent

    skills_cfg = config["skills"]
    base_dir = Path(skills_cfg["base_dir"])

    if skills_label == "baseline":
        # Empty temp dir = no learned skills
        tmp_root = Path(tempfile.mkdtemp(prefix="eval_test_baseline_"))
        learned_dir = tmp_root / "learned"
        learned_dir.mkdir()
        cleanup_tmp = tmp_root
    elif skills_label == "best":
        best_dir = run_dir / "skills" / "best"
        if not best_dir.exists():
            raise FileNotFoundError(f"Best skills dir not found: {best_dir}")
        tmp_root = Path(tempfile.mkdtemp(prefix="eval_test_best_"))
        learned_dir = tmp_root / "learned"
        shutil.copytree(best_dir, learned_dir)
        cleanup_tmp = tmp_root
    elif skills_label.startswith("epoch_"):
        # Use the skills that were active *after* this epoch (i.e. run's learned/ after
        # training, which for a completed run = the best checkpoint restored to learned/).
        # For a specific epoch, we'd need to replay — not supported; use best instead.
        raise ValueError("Per-epoch skill snapshots are not stored; use 'baseline' or 'best'")
    else:
        raise ValueError(f"Unknown skills label: {skills_label!r}. Use 'baseline' or 'best'")

    try:
        skill_repo = SkillRepository(base_dir=base_dir, learned_dir=learned_dir)
        learned_count = skill_repo.learned_count()
        print(f"  Skills: {learned_count} learned + base from {base_dir}")

        task_cfg = config["task"]
        task_client = TaskClient(
            name=task_cfg["name"],
            controller_address=task_cfg["controller_address"],
        )

        # Re-resolve the backend from env (config.yaml stores only the preset
        # name, never expanded keys); --agent / GRASP_BACKEND can override it.
        if "agent" not in config:
            from src.agent_preset import resolve_agent
            config["agent"] = resolve_agent(
                config, cli_agent=agent, agents_dir=Path("configs/agents"),
            )
        base_agent = InstanceFactory(**config["agent"]).create()
        skill_aware_agent = SkillAwareAgent(base_agent, skill_repo)

        eval_module = config.get("eval", {}).get("module")
        eval_fn = None
        if eval_module:
            try:
                mod = importlib.import_module(eval_module)
                eval_fn = getattr(mod, "eval")
            except Exception as e:
                print(f"  [EvalTest] warning: could not load eval fn from {eval_module}: {e}")

        id_to_index = {s["id"]: s["id"] for s in test_data}
        total = len(test_data)
        results = [None] * total

        import time

        def run_one(idx, sample):
            task_index = id_to_index[sample["id"]]
            from src.client.task import TaskError
            for attempt in range(3):
                result = task_client.run_sample(task_index, skill_aware_agent)
                if result.error != TaskError.NOT_AVAILABLE.value:
                    break
                time.sleep(5 * (attempt + 1))
            is_correct = _score_result(sample, result, eval_fn)
            status = result.output.status if result.output else result.error
            task_result = result.output.result if result.output else None
            return idx, is_correct, status, task_result

        correct = 0
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(run_one, i, s): i for i, s in enumerate(test_data)}
            done = 0
            for future in as_completed(futures):
                idx, is_correct, status, task_result = future.result()
                results[idx] = {
                    "sample_id": test_data[idx]["id"],
                    "is_correct": is_correct,
                    "status": status,
                    "result": task_result,
                }
                if is_correct:
                    correct += 1
                done += 1
                if done % 10 == 0 or done == total:
                    print(f"  [{done}/{total}] correct so far: {correct}")

        score = correct / total if total > 0 else 0.0
        score_record = {
            "skills": skills_label,
            "score": score,
            "n_correct": correct,
            "n_total": total,
            "test_split": str(test_path),
        }

        # Write outputs
        runs_path = run_dir / f"test_runs_{skills_label}.jsonl"
        with open(runs_path, "w", encoding="utf-8") as f:
            for entry in results:
                f.write(json.dumps(entry) + "\n")

        score_path = run_dir / f"test_score_{skills_label}.json"
        with open(score_path, "w", encoding="utf-8") as f:
            json.dump(score_record, f, indent=2)

        print(f"  Test score ({skills_label}): {score:.1%} ({correct}/{total})")
        print(f"  Saved: {score_path}")
        return score_record

    finally:
        if cleanup_tmp and cleanup_tmp.exists():
            shutil.rmtree(cleanup_tmp, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Test-set evaluation for a GRASP run")
    parser.add_argument("--run", "-r", required=True, help="Path to run directory")
    parser.add_argument(
        "--skills", "-s", default="best",
        choices=["baseline", "best"],
        help="Which skills to use: 'baseline' (no learned skills) or 'best' (best val checkpoint)",
    )
    parser.add_argument("--concurrency", "-j", type=int, default=8)
    parser.add_argument(
        "--controller-address", type=str, default=None, metavar="URL",
        help="Override task.controller_address from the saved config, "
             "e.g. http://localhost:5200/api",
    )
    parser.add_argument(
        "--agent", "-a", type=str, default=None, metavar="PRESET",
        help="Backend preset override (default: the run's agent_preset). "
             "See configs/agents/README.md.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run)
    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\nEvaluating test set for: {run_dir}")
    print(f"Skills: {args.skills}")
    record = run_test_eval(run_dir, args.skills, concurrency=args.concurrency,
                           controller_address=args.controller_address, agent=args.agent)
    print(f"\nDone: {record['score']:.4f} ({record['n_correct']}/{record['n_total']})")


if __name__ == "__main__":
    main()
