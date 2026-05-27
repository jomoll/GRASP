from __future__ import annotations

import json
from typing import Any, Dict, List

from .pipeline_adapter import ExPeLPipelineAdapter


class ExPeLAwareAgent:
    """Wrap an AgentClient and inject ExpeL rules on each call."""

    def __init__(self, agent: Any, pipeline_adapter: ExPeLPipelineAdapter) -> None:
        self.agent = agent
        self.pipeline_adapter = pipeline_adapter

    def inference(self, history: List[dict], tools=None):
        modified = [self._message_to_dict(m) for m in history]
        rule_block = self.pipeline_adapter.build_rule_block()

        if rule_block:
            # Inject on the first user/system turn before the agent has spoken
            first_user_idx = next(
                (i for i, m in enumerate(modified) if m.get("role") in ("user", "system")),
                None,
            )
            is_first_decision = not any(
                m.get("role") in ("assistant", "agent") for m in modified
            )
            if first_user_idx is not None and is_first_decision:
                existing = str(modified[first_user_idx].get("content") or "")
                try:
                    prompt_data = json.loads(existing)
                    prompt_data["behavioral_skills"] = rule_block
                    new_content = json.dumps(prompt_data, indent=2)
                except (json.JSONDecodeError, TypeError, AttributeError):
                    new_content = rule_block + "\n\n## Current Task\n" + existing
                modified[first_user_idx] = dict(
                    modified[first_user_idx],
                    content=new_content,
                )

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
