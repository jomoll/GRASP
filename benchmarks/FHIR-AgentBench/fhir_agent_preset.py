"""
Backend selection for FHIR-AgentBench runs.

Unlike the AgentBench/MedAgentBench harnesses (which build an agent from a
``{module, parameters}`` block), FHIR-AgentBench drives a LiteLLM-style agent
configured by a flat ``model`` (+ optional ``base_url``) on the ``agent``,
``updater``, and ``eval`` config blocks, plus ``project_id``/``location`` on
``agent`` for Vertex.

``apply_backend`` selects a preset (``configs/agents/<name>.yaml``) and merges
its ``model``/``base_url``/``project_id``/``location`` into those blocks,
keeping all other tuning keys (temperature, timeouts, ...) intact. The same
model then serves as executing agent, skill-writer, and grader, matching the
paper's setup. Precedence:

    --agent CLI flag   >   GRASP_BACKEND env var   >   config["agent_preset"]

Presets carry no secrets; endpoints/projects come from environment variables
via ``${VAR}`` / ``${VAR:-default}`` placeholders. If no backend is selected,
the config's inline ``agent`` block is left untouched.
"""

import os
import re
from pathlib import Path

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _expand_env(obj):
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


def resolve_backend_name(config: dict, cli_agent: str = None):
    """Effective backend name (precedence: CLI > GRASP_BACKEND > config)."""
    return cli_agent or os.environ.get("GRASP_BACKEND") or config.get("agent_preset")


def apply_backend(config: dict, cli_agent: str = None, agents_dir="configs/agents") -> None:
    """Merge the selected backend preset into config in place. No-op if none."""
    name = resolve_backend_name(config, cli_agent)
    if not name:
        return

    base = Path(agents_dir)
    preset_path = base / f"{name}.yaml"
    if not preset_path.exists():
        available = sorted(p.stem for p in base.glob("*.yaml"))
        raise SystemExit(
            f"Unknown backend '{name}'. Expected {preset_path}. "
            f"Available: {', '.join(available) or '(none)'}"
        )

    preset = _expand_env(yaml.safe_load(preset_path.read_text()))
    config["agent_preset"] = name

    # Same model for executor, skill-writer (updater), and grader (eval).
    for block_name in ("agent", "updater", "eval"):
        block = config.get(block_name)
        if not isinstance(block, dict):
            continue
        if preset.get("model"):
            block["model"] = preset["model"]
        if preset.get("base_url"):
            block["base_url"] = preset["base_url"]
        else:
            block.pop("base_url", None)

    # project_id / location are read from the agent block (Vertex only).
    agent = config.setdefault("agent", {})
    for key in ("project_id", "location"):
        if preset.get(key):
            agent[key] = preset[key]
        else:
            agent.pop(key, None)
