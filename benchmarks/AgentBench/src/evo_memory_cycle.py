"""
Entry point for the Evo-style structured memory comparator on AgentBench.

Usage:
    python -m src.evo_memory_cycle --config configs/evo_memory_cycle_os.yaml --run-name evo_001
"""

import argparse
import datetime
import sys
from pathlib import Path

import yaml


def main():
    parser = argparse.ArgumentParser(description="Evo memory cycle for AgentBench")
    parser.add_argument("--config", "-c", type=str, default="configs/evo_memory_cycle_os.yaml")
    parser.add_argument("--run-name", "-n", type=str, default=None)
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--resume", "-r", action="store_true")
    args = parser.parse_args()
    if args.force and args.resume:
        print("--force and --resume are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with config_path.open() as f:
        config = yaml.safe_load(f)

    run_name = args.run_name or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.get("output_dir", "outputs/evo_memory_cycle"))
    run_dir = output_dir / run_name

    if run_dir.exists() and not args.force and not args.resume:
        print(
            f"Run directory already exists: {run_dir}\n"
            "Use --resume to continue or --force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    run_dir.mkdir(parents=True, exist_ok=True)
    config["_resume"] = args.resume
    print(f"Run directory: {run_dir}")

    with (run_dir / "config.yaml").open("w") as f:
        yaml.dump(config, f, default_flow_style=False)

    cycle_cfg = config.get("cycle", {})
    evo_cfg = config.get("evo_memory", {})
    print(f"Epochs:          {cycle_cfg.get('epochs')}")
    print(f"Val concurrency: {cycle_cfg.get('batch_concurrency')} threads")
    print(f"Semantic top-k:  {evo_cfg.get('semantic_top_k', 8)}")
    print(f"Episodic top-k:  {evo_cfg.get('episodic_top_k', 3)}")
    print(f"Dev split:       {config['data']['dev']}")
    print(f"Val split:       {config['data']['val']}")

    from src.evo_memory.cycle import EvoMemoryCycleRunner

    runner = EvoMemoryCycleRunner(config=config, run_dir=run_dir)
    runner.run()


if __name__ == "__main__":
    main()
