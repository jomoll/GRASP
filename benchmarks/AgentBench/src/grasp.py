"""
Entry point for GRASP — the skill-learning cycle on AgentBench environments.

Usage:
    python -m src.grasp --config configs/grasp_os.yaml --run-name run_001 --agent gptoss

The model backend is selected with --agent (or the GRASP_BACKEND env var, or the
config's agent_preset:). See configs/agents/README.md for the available presets.

The task worker must already be running before invoking this script.
Start it with:
    python -m src.start_task -a --config configs/start_skill_task_os.yaml

Data splits must exist before running. Generate them with:
    python data/os_interaction/split_dataset.py
"""

import argparse
import datetime
import sys
from pathlib import Path

import yaml

from src.agent_preset import resolve_agent, resolve_backend_name


def _apply_overrides(config: dict, overrides) -> None:
    """Apply `key.subkey=value` overrides onto config (value parsed as YAML)."""
    for item in overrides or []:
        if "=" not in item:
            print(f"Invalid --set value (expected key=value): {item}", file=sys.stderr)
            sys.exit(1)
        key, _, raw = item.partition("=")
        keys = key.split(".")
        node = config
        for k in keys[:-1]:
            if k not in node or not isinstance(node[k], dict):
                node[k] = {}
            node = node[k]
        node[keys[-1]] = yaml.safe_load(raw)


def main():
    parser = argparse.ArgumentParser(
        description="GRASP skill-learning cycle for AgentBench environments"
    )
    parser.add_argument(
        "--config", "-c", type=str, default="configs/grasp_os.yaml",
        help="Path to GRASP config file",
    )
    parser.add_argument(
        "--agent", "-a", type=str, default=None, metavar="PRESET",
        help="Backend preset (configs/agents/<PRESET>.yaml): gptoss, deepseek, "
             "gemini, gpt4, gpt5, local. Overrides GRASP_BACKEND and the "
             "config's agent_preset.",
    )
    parser.add_argument(
        "--run-name", "-n", type=str, default=None,
        help="Run name (default: timestamp)",
    )
    parser.add_argument(
        "--force", "-f", action="store_true",
        help="Overwrite an existing run directory",
    )
    parser.add_argument(
        "--resume", "-r", action="store_true",
        help="Continue an interrupted run, skipping already-completed epochs",
    )
    parser.add_argument(
        "--controller-address", type=str, default=None, metavar="URL",
        help="Override task.controller_address, e.g. http://localhost:5200/api "
             "(point this run at a specific task worker/controller)",
    )
    parser.add_argument(
        "--set", metavar="KEY=VALUE", nargs="*", default=[],
        help="Override config values, e.g. task.controller_address=http://localhost:5200/api",
    )
    args = parser.parse_args()
    if args.force and args.resume:
        print("--force and --resume are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path) as f:
        config = yaml.safe_load(f)
    _apply_overrides(config, args.set)
    if args.controller_address:
        config.setdefault("task", {})["controller_address"] = args.controller_address

    # Resolve the model backend (CLI --agent > GRASP_BACKEND env > config.agent_preset).
    # Resolve now to fail fast on missing env vars, but keep the expanded block
    # (which may contain API keys/endpoints) out of the saved config.yaml — only
    # the preset name is persisted, and the agent is re-resolved from env at eval time.
    agent_block = resolve_agent(config, config_path, cli_agent=args.agent)
    backend_name = resolve_backend_name(config, args.agent)
    config["agent_preset"] = backend_name

    run_name = args.run_name or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.get("output_dir", "outputs/grasp"))
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

    with open(run_dir / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Inject the resolved (env-expanded) agent only after config.yaml is written.
    config["agent"] = agent_block

    cycle_cfg = config.get("cycle", {})
    _agent_params = agent_block.get("parameters", {})
    _model = _agent_params.get("model") or _agent_params.get("body", {}).get("model")
    print(f"Backend:       {backend_name} -> {agent_block['module'].rsplit('.', 1)[-1]} ({_model})")
    print(f"Epochs:        {cycle_cfg.get('epochs')}")
    print(f"Update every:  {cycle_cfg.get('update_every')} samples")
    print(f"Concurrency:   {cycle_cfg.get('batch_concurrency')} threads")
    print(f"Max proposals: {cycle_cfg.get('max_proposals')}")
    print(f"Dev split:     {config['data']['dev']}")
    print(f"Val split:     {config['data']['val']}")

    from src.skills.cycle import SkillCycleRunner
    runner = SkillCycleRunner(config=config, run_dir=run_dir)
    runner.run()


if __name__ == "__main__":
    main()
