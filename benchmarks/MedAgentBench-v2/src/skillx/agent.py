from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _overlap_score(query: str, doc: str) -> float:
    q = set(_tokenize(query))
    d = set(_tokenize(doc))
    if not q or not d:
        return 0.0
    return len(q & d) / len(q | d)


class SkillXAwareAgent:
    """Wrap an AgentClient and inject retrieved SkillX skills on each call."""

    def __init__(self, agent: Any, library_path: Path, top_k: int = 5) -> None:
        self.agent = agent
        self.library_path = Path(library_path)
        self.top_k = top_k

    def inference(self, history: List[dict], tools=None):
        modified = [self._message_to_dict(m) for m in history]
        last_user_idx = max(
            (i for i, m in enumerate(modified) if m.get("role") in ("user", "system")),
            default=0,
        )
        query = str(modified[last_user_idx].get("content") or "")
        skill_block = self._build_skill_block(query)

        if not skill_block:
            return self._delegate(modified, tools=tools)

        is_first_decision = not any(
            m.get("role") in ("assistant", "agent")
            for m in modified[:last_user_idx + 1]
        )
        existing = modified[last_user_idx].get("content") or ""
        if is_first_decision:
            try:
                prompt_data = json.loads(existing)
                prompt_data["behavioral_skills"] = skill_block
                new_content = json.dumps(prompt_data, indent=2)
            except (json.JSONDecodeError, TypeError, AttributeError):
                new_content = skill_block + "\n\n## Current Task\n" + existing
        else:
            new_content = existing + "\n\n" + skill_block
        modified[last_user_idx] = dict(modified[last_user_idx], content=new_content)
        return self._delegate(modified, tools=tools)

    def _build_skill_block(self, query: str) -> str:
        skills = self._retrieve(query)
        if not skills:
            return ""
        parts = ["<skillx_memory>\nBehavioral skills extracted from past experience:\n"]
        for skill in skills:
            parts.append(f"### {skill['name']}\n{skill['document']}\n\n```\n{skill['content']}\n```\n")
        parts.append("</skillx_memory>")
        return "\n".join(parts)

    def _retrieve(self, query: str) -> List[Dict[str, Any]]:
        if not self.library_path.exists():
            return []
        try:
            with self.library_path.open(encoding="utf-8") as f:
                data = json.load(f)
            skills = data.get("skills", {}).get("functional", [])
        except Exception:
            return []
        if not skills:
            return []
        scored = [
            (
                _overlap_score(query, f"{s.get('name', '')} {s.get('document', '')}"),
                s,
            )
            for s in skills
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:self.top_k] if scored[0][0] > 0]

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
