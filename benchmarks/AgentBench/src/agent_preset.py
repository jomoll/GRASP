"""
Backend selection for GRASP runs.

A run's executing/skill-writing model is chosen at run time rather than baked
into each task config. Task configs carry a single ``agent_preset:`` key (a
default backend); the actual backend is resolved with this precedence:

    --agent CLI flag   >   GRASP_BACKEND env var   >   config["agent_preset"]

The resolved name maps to ``configs/agents/<name>.yaml``, which holds a full
agent block (``module`` + ``parameters``) for one provider. Preset files use
``${VAR}`` / ``${VAR:-default}`` placeholders so no API keys, endpoints, or
project identifiers are ever stored in the repository — they are read from the
environment at run time (see configs/agents/README.md).

If a task config additionally sets ``agent_temperature:``, it is written into
the resolved block at the backend-appropriate location, which preserves the
per-task decoding settings used in the paper regardless of backend.
"""

import os
import re
from pathlib import Path

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _expand_env(obj):
    """Recursively expand ``${VAR}`` / ``${VAR:-default}`` in strings."""
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env(v) for v in obj]
    if isinstance(obj, str):
        def repl(m):
            var, default = m.group(1), m.group(2)
            val = os.environ.get(var)
            if val is None:
                if default is None:
                    raise KeyError(
                        f"Environment variable '{var}' is required by the selected "
                        f"agent preset but is not set."
                    )
                return default
            return val
        return _ENV_PATTERN.sub(repl, obj)
    return obj


def _agents_dir(config_path, agents_dir) -> Path:
    if agents_dir is not None:
        return Path(agents_dir)
    return Path(config_path).resolve().parent / "agents"


def resolve_backend_name(config: dict, cli_agent: str = None):
    """Effective backend name (precedence: CLI > GRASP_BACKEND > config)."""
    return cli_agent or os.environ.get("GRASP_BACKEND") or config.get("agent_preset")


def _apply_temperature(agent: dict, temperature) -> None:
    """Place a task-level temperature at the backend-appropriate location."""
    params = agent.setdefault("parameters", {})
    if isinstance(params.get("body"), dict):  # HTTP / OpenAI-compatible
        params["body"]["temperature"] = temperature
    else:  # LiteLLM / Vertex / Responses
        params["temperature"] = temperature


def resolve_agent(config: dict, config_path=None, cli_agent: str = None,
                  agents_dir=None) -> dict:
    """Return the resolved, env-expanded agent block for this run.

    Precedence: ``cli_agent`` > ``GRASP_BACKEND`` env > ``config['agent_preset']``.
    Falls back to an inline ``config['agent']`` block if no preset is selected
    (kept for backward compatibility with hand-written configs).

    ``agents_dir`` overrides where ``<name>.yaml`` presets are looked up; by
    default they sit next to the config in ``<config dir>/agents/``.
    """
    name = resolve_backend_name(config, cli_agent)

    if not name:
        if "agent" in config:
            return _expand_env(config["agent"])
        raise SystemExit(
            "No backend selected: pass --agent NAME, set GRASP_BACKEND, or add "
            "'agent_preset:' to the config. Available presets live in configs/agents/."
        )

    base = _agents_dir(config_path, agents_dir)
    preset_path = base / f"{name}.yaml"
    if not preset_path.exists():
        available = sorted(p.stem for p in base.glob("*.yaml"))
        raise SystemExit(
            f"Unknown backend '{name}'. Expected {preset_path}. "
            f"Available: {', '.join(available) or '(none)'}"
        )

    with open(preset_path) as f:
        agent = yaml.safe_load(f)

    agent = _expand_env(agent)
    if config.get("agent_temperature") is not None:
        _apply_temperature(agent, config["agent_temperature"])
    return agent
