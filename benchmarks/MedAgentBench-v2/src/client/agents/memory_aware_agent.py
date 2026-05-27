"""
MemoryAwareAgent — wraps any AgentClient and injects the current memory bullets
into the conversation history before each inference call.

Injection strategy mirrors SkillAwareAgent:
  First decision turn:  prepended before the task instruction.
  Continuation turns:   appended after the latest environment observation.

The memory file (memory.json) is re-read on every call so updates written by
MemoryUpdater after the previous batch are immediately visible.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from ..agent import AgentClient
from ...memory.updater import _normalise_memory_list


class MemoryAwareAgent(AgentClient):
    def __init__(self, agent: AgentClient, memory_path: Path) -> None:
        super().__init__()
        self.agent = agent
        self.memory_path = Path(memory_path)

    def _load_memory_block(self) -> str:
        if not self.memory_path.exists():
            return ""
        try:
            bullets = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return ""
        bullets = _normalise_memory_list(bullets)
        if not bullets:
            return ""
        lines = ["<memory>", "Correction notes from past experience:"]
        lines += [f"- {b}" for b in bullets]
        lines.append("</memory>")
        return "\n".join(lines)

    def inference(self, history: List[dict], tools=None):
        memory_block = self._load_memory_block()
        if not memory_block:
            return self._delegate(history, tools=tools)

        modified = [self._message_to_dict(m) for m in history]
        last_user_idx = max(
            (i for i, m in enumerate(modified) if m.get("role") in ("user", "system")),
            default=0,
        )
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
                new_content = memory_block + "\n\n" + existing
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
