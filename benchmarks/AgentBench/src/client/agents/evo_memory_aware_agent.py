from __future__ import annotations

import json
from typing import Any, Dict, List

from ..agent import AgentClient
from src.evo_memory.core import EvoMemoryCore


class EvoMemoryAwareAgent(AgentClient):
    """Wrap an AgentClient and inject retrieved Evo memory context on each call."""

    def __init__(self, agent: AgentClient, memory_core: EvoMemoryCore) -> None:
        super().__init__()
        self.agent = agent
        self.memory_core = memory_core

    def inference(self, history: List[dict], tools=None):
        modified = [self._message_to_dict(m) for m in history]
        last_user_idx = max(
            (i for i, m in enumerate(modified) if m.get("role") in ("user", "system")),
            default=0,
        )
        query = str(modified[last_user_idx].get("content") or "")
        memory_block = self.memory_core.build_context(query)
        if not memory_block:
            return self._delegate(modified, tools=tools)

        is_first_decision = not any(
            m.get("role") in ("assistant", "agent")
            for m in modified[:last_user_idx + 1]
        )
        existing = modified[last_user_idx].get("content") or ""
        if is_first_decision:
            try:
                prompt_data = json.loads(existing)
                prompt_data["behavioral_skills"] = memory_block
                new_content = json.dumps(prompt_data, indent=2)
            except (json.JSONDecodeError, TypeError, AttributeError):
                new_content = memory_block + "\n\n## Current Task\n" + existing
        else:
            new_content = existing + "\n\n" + memory_block
        modified[last_user_idx] = dict(modified[last_user_idx], content=new_content)
        return self._delegate(modified, tools=tools)

    def _delegate(self, history: List[dict], tools=None):
        if tools is not None:
            try:
                return self.agent.inference(history, tools=tools)
            except TypeError:
                pass
        return self.agent.inference(history)

    @staticmethod
    def _message_to_dict(message: Any) -> Dict[str, Any]:
        if isinstance(message, dict):
            return dict(message)
        if hasattr(message, "model_dump"):
            return message.model_dump(exclude_none=True)
        if hasattr(message, "dict"):
            return message.dict(exclude_none=True)
        return {
            "role": getattr(message, "role", "user"),
            "content": getattr(message, "content", ""),
        }
