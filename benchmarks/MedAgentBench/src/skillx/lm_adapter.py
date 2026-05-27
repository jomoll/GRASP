from __future__ import annotations

import asyncio
from typing import Any, Dict, List


def _msg_to_dict(message: Any) -> Dict[str, Any]:
    """Convert LangChain message objects or tuples to role/content dicts."""
    if isinstance(message, dict):
        role = message.get("role", "user")
        content = message.get("content", "")
    elif isinstance(message, tuple) and len(message) == 2:
        role_raw, content = message
        role = str(role_raw)
    elif hasattr(message, "type"):
        role_map = {"human": "user", "ai": "assistant", "system": "system"}
        role = role_map.get(message.type, message.type)
        content = getattr(message, "content", "")
    else:
        role = getattr(message, "role", "user")
        content = getattr(message, "content", "")

    role_map = {"human": "user", "ai": "assistant", "agent": "assistant"}
    role = role_map.get(role, role)
    return {"role": role, "content": str(content)}


class SkillXLLMAdapter:
    """Bridge a sync AgentClient to the async ainvoke() interface SkillX expects."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    async def ainvoke(self, messages: List[Any], **kwargs) -> str:
        history = [_msg_to_dict(m) for m in messages]
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.agent.inference, history)
        return result or ""
