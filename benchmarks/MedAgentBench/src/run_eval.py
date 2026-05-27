"""
Evaluate the base agent or a saved skill pack on any data split.

Usage:
    # Base agent (no learned skills) on the test set
    python -m src.run_eval --config configs/grasp.yaml --split test --run-name base_test

    # Agent with best skills from a completed run on the test set
    python -m src.run_eval --config configs/grasp.yaml --split test \\
        --skills-dir outputs/grasp_gptoss/run_001/skills/best --run-name run_001_best_test

    # Resume an interrupted run
    python -m src.run_eval --config configs/grasp.yaml --split test \\
        --run-name base_test --resume

The task worker must already be running before invoking this script.
"""

import argparse
import datetime
import json
import shutil
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from src.client.agents.skill_aware_agent import SkillAwareAgent
from src.client.task import TaskClient
from src.skills.cycle import _load_required_json_list, _score_result
from src.skills.repository import SkillRepository
from src.typings.general import InstanceFactory

try:
    from tqdm import tqdm
except Exception:
    tqdm = None


def _run_one(sample, index, task_client, agent, fhir_api_base):
    from src.client.task import TaskError
    for attempt in range(3):
        result = task_client.run_sample(index, agent)
        if result.error != TaskError.NOT_AVAILABLE.value:
            break
        time.sleep(5 * (attempt + 1))
    is_correct = _score_result(sample, result, fhir_api_base)
    return {
        "sample_id": sample["id"],
        "is_correct": is_correct,
        "error": result.error,
        "status": result.output.status if result.output else None,
        "result": result.output.result if result.output else None,
    }


def _load_completed(jsonl_path: Path) -> dict:
    completed = {}
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                entry = json.loads(line)
                completed[str(entry["sample_id"])] = entry
    return completed


def main():
    parser = argparse.ArgumentParser(description="Evaluate base or skilled agent on a data split")
    parser.add_argument("--config", "-c", type=str, default="configs/grasp.yaml")
    parser.add_argument("--agent", "-a", type=str, default=None, metavar="PRESET",
                        help="Backend preset (configs/agents/<PRESET>.yaml); overrides GRASP_BACKEND and agent_preset.")
    parser.add_argument("--split", "-s", choices=["dev", "val", "test", "id_test"], default="test")
    parser.add_argument(
        "--skills-dir", type=str, default=None,
        help="Path to a learned-skills directory. Omit to run the base agent.",
    )
    parser.add_argument("--run-name", "-n", type=str, default=None)
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--resume", "-r", action="store_true",
                        help="Skip already-completed samples and continue writing to the existing JSONL.")
    parser.add_argument("--controller-address", type=str, default=None,
                        help="Override task.controller_address from the config.")
    args = parser.parse_args()

    if args.force and args.resume:
        print("--force and --resume are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Resolve the model backend from the selected preset (configs carry only
    # an agent_preset name, not an inline agent block).
    from src.agent_preset import resolve_agent
    config["agent"] = resolve_agent(config, config_path, cli_agent=args.agent)

    split_key = args.split
    if split_key not in config.get("data", {}):
        print(f"Split '{split_key}' not found in config data section.", file=sys.stderr)
        sys.exit(1)

    run_name = args.run_name or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("outputs") / "eval" / run_name
    if run_dir.exists() and not args.force and not args.resume:
        print(f"Run directory already exists: {run_dir}\nUse --force to overwrite or --resume to continue.", file=sys.stderr)
        sys.exit(1)
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False)

    full_data = _load_required_json_list(Path(config["data"]["full"]), "full dataset")
    id_to_index = {s["id"]: i for i, s in enumerate(full_data)}

    samples = _load_required_json_list(Path(config["data"][split_key]), f"{split_key} split")

    jsonl_path = run_dir / f"{split_key}_runs.jsonl"
    completed = _load_completed(jsonl_path) if args.resume else {}
    pending = [s for s in samples if str(s["id"]) not in completed]

    if args.resume:
        print(f"Resuming: {len(completed)} already done, {len(pending)} remaining.")

    task_cfg = config["task"]
    fhir_api_base = task_cfg["fhir_api_base"]
    controller_address = args.controller_address or task_cfg["controller_address"]
    task_client = TaskClient(name=task_cfg["name"], controller_address=controller_address)

    _tmpdir = None
    if args.skills_dir:
        learned_dir = Path(args.skills_dir)
    else:
        _tmpdir = tempfile.mkdtemp(prefix="run_eval_base_")
        learned_dir = Path(_tmpdir)

    skill_repo = SkillRepository(base_dir=Path(config["skills"]["base_dir"]), learned_dir=learned_dir)
    base_agent = InstanceFactory(**config["agent"]).create()
    agent = SkillAwareAgent(base_agent, skill_repo)

    concurrency = int(config.get("cycle", {}).get("batch_concurrency", 1))
    mode = f"skills ({args.skills_dir})" if args.skills_dir else "base (no learned skills)"
    print(f"Run directory: {run_dir}")
    print(f"Split:         {split_key} ({len(samples)} samples)")
    print(f"Mode:          {mode}")
    print(f"Task:          {task_cfg['name']}")
    print(f"Concurrency:   {concurrency}")

    write_lock = threading.Lock()

    with open(jsonl_path, "a", encoding="utf-8") as jsonl_f:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_run_one, s, id_to_index[s["id"]], task_client, agent, fhir_api_base): s
                for s in pending
            }
            done = len(completed)
            total = len(samples)
            for future in as_completed(futures):
                entry = future.result()
                with write_lock:
                    jsonl_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    jsonl_f.flush()
                    completed[str(entry["sample_id"])] = entry
                done += 1
                if done % 10 == 0 or done == total:
                    n_correct = sum(1 for x in completed.values() if x["is_correct"])
                    print(f"[{done}/{total}] correct={n_correct}")

    if _tmpdir:
        shutil.rmtree(_tmpdir, ignore_errors=True)

    all_results = list(completed.values())
    n_correct = sum(1 for x in all_results if x["is_correct"])
    summary = {
        "split": split_key,
        "score": n_correct / len(all_results) if all_results else 0.0,
        "n_correct": n_correct,
        "n_total": len(all_results),
        "skills_dir": args.skills_dir,
    }
    with open(run_dir / f"{split_key}_score.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Final: {n_correct}/{len(all_results)} ({summary['score']:.1%})")


if __name__ == "__main__":
    main()
