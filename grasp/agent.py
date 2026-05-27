"""
Agent contract and construction.

An *agent* is anything exposing ``inference(history, tools=None) -> response``,
where ``history`` is a list of chat-style ``{"role", "content"}`` messages.
:class:`AgentClient` is the nominal base class, but any object with that method
works (the loop wraps it for skill injection).

:func:`build_agent` instantiates an agent from a config block of the form
``{"module": "pkg.mod.ClassName", "parameters": {...}}`` — the same shape the
paper benchmarks use, so backend presets are portable between them and the core.
"""

import builtins
import importlib
from typing import Any, Dict, List


class AgentClient:
    """Base class for agents. Subclass and implement :meth:`inference`."""

    def __init__(self, *args, **kwargs):
        pass

    def inference(self, history: List[dict], tools=None) -> str:
        raise NotImplementedError()


def build_agent(agent_block: Dict[str, Any]):
    """Instantiate an agent from a ``{"module", "parameters"}`` block.

    ``module`` is either a dotted path to a class (``pkg.mod.ClassName``) or a
    bare builtin name; ``parameters`` are passed as keyword arguments.
    """
    module = agent_block["module"]
    parameters = agent_block.get("parameters") or {}
    if "." in module:
        path, _, cls_name = module.rpartition(".")
        mod = importlib.import_module(path)
        cls = getattr(mod, cls_name)
    else:
        cls = getattr(builtins, module)
    return cls(**parameters)
