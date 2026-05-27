"""
Run a fixed manual skill pack against an AgentBench task split.

Usage:
    python -m src.run_manual_skills --config configs/manual_skills_dbbench.yaml --split val

The task worker must already be running, for example:
    python -m src.start_task -a --config configs/start_skill_task_dbbench.yaml
"""

import argparse
import datetime
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from src.client.agents.skill_aware_agent import SkillAwareAgent
from src.client.task import TaskClient
from src.skills.cycle import _load_eval_fn, _load_required_json_list, _score_result
from src.skills.repository import SkillRepository
from src.typings.general import InstanceFactory

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - optional dependency
    tqdm = None


def _serialize_history(history):
    if not history:
        return []
    out = []
    for msg in history:
        if isinstance(msg, dict):
            out.append(msg)
        elif hasattr(msg, "__dict__"):
            out.append(vars(msg))
        else:
            out.append({"role": "unknown", "content": str(msg)})
    return out


def _run_one(sample, task_client, agent, eval_fn):
    result = task_client.run_sample(sample["id"], agent)
    is_correct = _score_result(sample, result, eval_fn)
    return {
        "sample_id": sample["id"],
        "is_correct": is_correct,
        "error": result.error,
        "status": result.output.status if result.output else None,
        "result": result.output.result if result.output else None,
        "history": _serialize_history(result.output.history if result.output else None),
    }


def main():
    parser = argparse.ArgumentParser(description="Run a manual skill pack on a task split")
    parser.add_argument(
        "--config", "-c", type=str, default="configs/manual_skills_dbbench.yaml",
        help="Path to config file",
    )
    parser.add_argument(
        "--split", "-s", choices=["dev", "val"], default="val",
        help="Which configured split to evaluate",
    )
    parser.add_argument(
        "--run-name", "-n", type=str, default=None,
        help="Output run name (default: timestamp)",
    )
    parser.add_argument(
        "--force", "-f", action="store_true",
        help="Overwrite an existing run directory",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    run_name = args.run_name or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(config.get("output_dir", "outputs/manual_skills")) / run_name
    if run_dir.exists() and not args.force:
        print(
            f"Run directory already exists: {run_dir}\nUse --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False)

    split_path = Path(config["data"][args.split])
    samples = _load_required_json_list(split_path, f"{args.split} split")
    eval_fn = _load_eval_fn(config)

    task_client = TaskClient(
        name=config["task"]["name"],
        controller_address=config["task"]["controller_address"],
    )
    base_agent = InstanceFactory(**config["agent"]).create()
    skill_repo = SkillRepository(
        base_dir=Path(config["skills"]["base_dir"]),
        learned_dir=Path(config["skills"]["manual_dir"]),
    )
    agent = SkillAwareAgent(base_agent, skill_repo)

    batch_concurrency = int(config.get("run", {}).get("batch_concurrency", 1))
    results = [None] * len(samples)

    print(f"Run directory:   {run_dir}")
    print(f"Split:           {args.split}")
    print(f"Samples:         {len(samples)}")
    print(f"Task:            {config['task']['name']}")
    print(f"Manual skills:   {config['skills']['manual_dir']}")
    print(f"Concurrency:     {batch_concurrency}")

    progress_stream = sys.stderr if tqdm is not None and sys.stderr.isatty() else None
    completed = as_completed
    if progress_stream is not None:
        def completed(futures):
            return tqdm(
                as_completed(futures),
                total=len(futures),
                desc=f"{args.split} samples",
                file=progress_stream,
                dynamic_ncols=True,
            )

    with ThreadPoolExecutor(max_workers=batch_concurrency) as pool:
        futures = {pool.submit(_run_one, sample, task_client, agent, eval_fn): i for i, sample in enumerate(samples)}
        for idx, future in enumerate(completed(futures), start=1):
            sample_index = futures[future]
            entry = future.result()
            results[sample_index] = entry
            if idx % 10 == 0 or idx == len(samples):
                n_correct = sum(1 for x in results if x and x["is_correct"])
                print(f"[{idx}/{len(samples)}] correct={n_correct}")

    results_path = run_dir / f"{args.split}_runs.jsonl"
    with open(results_path, "w", encoding="utf-8") as f:
        for entry in results:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    n_correct = sum(1 for x in results if x["is_correct"])
    summary = {
        "split": args.split,
        "score": n_correct / len(results) if results else 0.0,
        "n_correct": n_correct,
        "n_total": len(results),
        "manual_dir": config["skills"]["manual_dir"],
    }
    with open(run_dir / f"{args.split}_score.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Final: {n_correct}/{len(results)} ({summary['score']:.1%})")


if __name__ == "__main__":
    main()
