"""
Evaluate the base agent or a saved skill pack on any FHIR-AgentBench data split.

Usage:
    # Base agent (no learned skills) on the test set
    python run_eval.py --config configs/grasp.yaml --split test --run-name base_test

    # Agent with best skills from a completed run on the test set
    python run_eval.py --config configs/grasp.yaml --split test \\
        --skills-dir outputs/grasp_gptoss/run_001/skills/best --run-name run_001_best_test

    # Resume an interrupted run
    python run_eval.py --config configs/grasp.yaml --split test \\
        --run-name run_001_best_test --resume
"""

import argparse
import datetime
import json
import logging
import os
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict

import yaml

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

sys.path.insert(0, str(Path(__file__).resolve().parent / "utils"))
from core_utils import parse_outputs

from skill_learning.agent import create_skill_aware_fhir_agent
from skill_learning.cycle import _load_samples
from skill_learning.evaluator import FHIRSampleEvaluator
from skill_learning.repository import SkillRepository

try:
    from tqdm import tqdm
except Exception:
    tqdm = None


def _run_one(sample: Dict, agent_cfg: Dict, skill_repo: SkillRepository, evaluator: FHIRSampleEvaluator) -> Dict:
    import tools.cache as cache_module
    cache_module.CACHE_ENABLED = bool(agent_cfg.get("enable_cache", True))
    agent = create_skill_aware_fhir_agent(
        agent_strategy=agent_cfg.get("strategy", "multi_turn_resource"),
        model=agent_cfg["model"],
        base_url=agent_cfg.get("base_url"),
        verbose=bool(agent_cfg.get("verbose", False)),
        skill_repo=skill_repo,
        timeout=int(agent_cfg.get("timeout", 20)),
        max_retries=int(agent_cfg.get("max_retries", 3)),
    )
    try:
        raw_output = agent.run(sample["question_with_context"])
        parsed = parse_outputs(raw_output)
    except Exception as e:
        parsed = {"agent_answer": None, "error": str(e)}
    is_correct = evaluator.score(sample, parsed)
    return {
        "sample_id": sample["question_id"],
        "is_correct": is_correct,
        "error": parsed.get("error"),
        "status": "completed" if not parsed.get("error") else "agent_error",
        "ground_truth": sample.get("true_answer"),
        "result": parsed.get("agent_answer"),
    }


def _load_completed(jsonl_path: Path) -> Dict[str, Dict]:
    completed = {}
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                entry = json.loads(line)
                completed[str(entry["sample_id"])] = entry
    return completed


def main():
    parser = argparse.ArgumentParser(description="Evaluate base or skilled agent on a FHIR-AgentBench split")
    parser.add_argument("--config", "-c", type=str, default="configs/grasp.yaml")
    parser.add_argument("--agent", "-a", type=str, default=None, metavar="PRESET",
                        help="Backend preset (configs/agents/<PRESET>.yaml); "
                             "overrides GRASP_BACKEND and agent_preset.")
    parser.add_argument("--split", "-s", choices=["dev", "val", "test"], default="test")
    parser.add_argument(
        "--skills-dir", type=str, default=None,
        help="Path to a learned-skills directory. Omit to run the base agent.",
    )
    parser.add_argument("--run-name", "-n", type=str, default=None)
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--resume", "-r", action="store_true",
                        help="Skip already-completed samples and continue writing to the existing JSONL.")
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

    # Apply the selected model backend (config carries only an agent_preset name).
    from fhir_agent_preset import apply_backend
    apply_backend(config, args.agent)

    agent_cfg = config["agent"]
    if agent_cfg.get("project_id"):
        os.environ["VERTEXAI_PROJECT"] = str(agent_cfg["project_id"])
    if agent_cfg.get("location"):
        os.environ["VERTEXAI_LOCATION"] = str(agent_cfg["location"])

    splits_config_key = f"{args.split}_splits"
    data_cfg = config.get("data", {})
    if splits_config_key not in data_cfg:
        print(f"'{splits_config_key}' not found in config data section.", file=sys.stderr)
        sys.exit(1)

    run_name = args.run_name or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("outputs") / "eval" / run_name
    if run_dir.exists() and not args.force and not args.resume:
        print(f"Run directory already exists: {run_dir}\nUse --force to overwrite or --resume to continue.", file=sys.stderr)
        sys.exit(1)
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False)

    split_names = data_cfg[splits_config_key]
    limit = data_cfg.get(f"{args.split}_limit")
    samples = _load_samples(Path(data_cfg["csv"]), split_names, limit)

    jsonl_path = run_dir / f"{args.split}_runs.jsonl"
    completed = _load_completed(jsonl_path) if args.resume else {}
    pending = [s for s in samples if str(s["question_id"]) not in completed]

    if args.resume:
        print(f"Resuming: {len(completed)} already done, {len(pending)} remaining.")

    eval_cfg = config.get("eval", {})
    evaluator = FHIRSampleEvaluator(
        model=eval_cfg.get("model", agent_cfg["model"]),
        base_url=eval_cfg.get("base_url", agent_cfg.get("base_url")),
        cache_path=run_dir / "eval_cache.json",
        timeout=int(eval_cfg.get("timeout", 20)),
        max_retries=int(eval_cfg.get("max_retries", 3)),
    )

    _tmpdir = None
    if args.skills_dir:
        learned_dir = Path(args.skills_dir)
    else:
        _tmpdir = tempfile.mkdtemp(prefix="run_eval_base_")
        learned_dir = Path(_tmpdir)

    skill_repo = SkillRepository(
        base_dir=Path(config["skills"]["base_dir"]),
        learned_dir=learned_dir,
    )

    concurrency = int(config.get("cycle", {}).get("batch_concurrency", 4))
    mode = f"skills ({args.skills_dir})" if args.skills_dir else "base (no learned skills)"
    print(f"Run directory: {run_dir}")
    print(f"Split:         {args.split} ({len(samples)} samples from {split_names})")
    print(f"Mode:          {mode}")
    print(f"Config:        {config_path}")
    print(f"Concurrency:   {concurrency}")

    import threading
    write_lock = threading.Lock()

    with open(jsonl_path, "a", encoding="utf-8") as jsonl_f:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(_run_one, s, agent_cfg, skill_repo, evaluator): s
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
        "split": args.split,
        "score": n_correct / len(all_results) if all_results else 0.0,
        "n_correct": n_correct,
        "n_total": len(all_results),
        "skills_dir": args.skills_dir,
    }
    with open(run_dir / f"{args.split}_score.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Final: {n_correct}/{len(all_results)} ({summary['score']:.1%})")


if __name__ == "__main__":
    main()
