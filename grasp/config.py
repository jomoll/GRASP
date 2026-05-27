"""
Config loading and run-directory setup, shared by every method entry point.

This generalizes the per-benchmark ``grasp.py`` launcher: load a YAML config,
apply ``key.subkey=value`` overrides, resolve the model backend (failing fast on
missing env vars), and prepare the run directory — persisting only the backend
*preset name* to ``config.yaml`` so resolved secrets never land on disk.
"""

import datetime
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import yaml

from .backends import resolve_agent, resolve_backend_name


def apply_overrides(config: Dict[str, Any], overrides: Optional[Iterable[str]]) -> None:
    """Apply ``key.subkey=value`` overrides onto ``config`` (value parsed as YAML)."""
    for item in overrides or []:
        if "=" not in item:
            print(f"Invalid override (expected key=value): {item}", file=sys.stderr)
            sys.exit(1)
        key, _, raw = item.partition("=")
        keys = key.split(".")
        node = config
        for k in keys[:-1]:
            if k not in node or not isinstance(node[k], dict):
                node[k] = {}
            node = node[k]
        node[keys[-1]] = yaml.safe_load(raw)


def load_config(config_path, overrides: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Load a YAML config and apply ``--set`` style overrides."""
    config_path = Path(config_path)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    apply_overrides(config, overrides)
    return config


def prepare_run(
    config_path,
    *,
    overrides: Optional[Iterable[str]] = None,
    cli_agent: Optional[str] = None,
    run_name: Optional[str] = None,
    force: bool = False,
    resume: bool = False,
    agents_dir=None,
) -> Tuple[Dict[str, Any], Path]:
    """Load config, resolve the backend, and create the run directory.

    Returns ``(config, run_dir)``. The returned config has the resolved,
    env-expanded ``agent`` block injected in memory, while the ``config.yaml``
    written to ``run_dir`` records only the preset name (``agent_preset``) — so
    the run is reproducible without persisting API keys or endpoints. The agent
    is re-resolved from the environment wherever it is needed.
    """
    if force and resume:
        print("force and resume are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    config_path = Path(config_path)
    config = load_config(config_path, overrides)

    # Resolve now to fail fast on missing env vars; persist only the preset name.
    agent_block = resolve_agent(config, config_path, cli_agent=cli_agent,
                                agents_dir=agents_dir)
    config["agent_preset"] = resolve_backend_name(config, cli_agent)

    run_name = run_name or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.get("output_dir", "runs"))
    run_dir = output_dir / run_name

    if run_dir.exists() and not force and not resume:
        print(
            f"Run directory already exists: {run_dir}\n"
            "Use resume to continue or force to overwrite.",
            file=sys.stderr,
        )
        sys.exit(1)

    run_dir.mkdir(parents=True, exist_ok=True)
    config["_resume"] = resume

    with open(run_dir / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Inject the resolved (env-expanded) agent only after config.yaml is written,
    # so secrets stay out of the persisted config.
    config["agent"] = agent_block
    return config, run_dir
