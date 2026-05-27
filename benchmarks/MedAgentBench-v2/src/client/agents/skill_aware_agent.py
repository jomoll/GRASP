"""
SkillAwareAgent — wraps any AgentClient and injects the current skill library
into the first user message before each inference call.

When the first message is a JSON-structured task prompt (as produced by
_build_task_prompt in the task server), skills are injected as a single
plain-text `behavioral_skills` field alongside the existing JSON fields:

    {
      "phase": "task_execution",
      "task": { ... },
      "behavioral_skills": "### skill_name\n*When to use: ...*\n\n...",
      "api": { ... },
      "response_format": { ... }
    }

If the first message is plain text (legacy format), skills are appended after
the task content, separated by a divider.

Skills named "skeleton" (the read-only base template) are never injected.
If no learned skills exist the history is passed through unchanged.
"""

import json
from typing import List

from ..agent import AgentClient
from src.skills.repository import SkillRepository


class SkillAwareAgent(AgentClient):
    def __init__(self, agent: AgentClient, skill_repo: SkillRepository) -> None:
        super().__init__()
        self.agent = agent
        self.skill_repo = skill_repo

    def inference(self, history: List[dict]) -> str:
        def _item_to_dict(item):
            if isinstance(item, dict):
                return item
            return {"role": item.role, "content": item.content}

        skills = [s for s in self.skill_repo.load_all() if s["name"] != "skeleton"]
        if not skills:
            return self.agent.inference([_item_to_dict(item) for item in history])

        modified = [_item_to_dict(item) for item in history]
        first_content = modified[0]["content"]
        skill_block = self._render_skills(skills)

        try:
            prompt_data = json.loads(first_content)
            # Remove legacy fields if present from prior runs
            prompt_data.pop("skill_instruction", None)
            prompt_data.pop("selected_skills", None)
            prompt_data.pop("skill_documentation", None)
            prompt_data["behavioral_skills"] = skill_block
            modified[0] = {"role": "user", "content": json.dumps(prompt_data, indent=2)}
        except (json.JSONDecodeError, TypeError, AttributeError):
            modified[0] = {
                "role": "user",
                "content": first_content + "\n\n" + skill_block,
            }

        return self.agent.inference(modified)

    @staticmethod
    def _render_skills(skills: List[dict]) -> str:
        header = (
            "---\n"
            "**Behavioral skills:** before each action, scan the skill descriptions "
            "below. If a skill's 'When to use' matches your current task or the action "
            "you are about to take, follow its guidance. Skip skills that do not match.\n"
        )
        blocks = []
        for s in skills:
            name = s["name"]
            desc = s.get("description", "")
            content = s.get("content", "")
            desc_line = f"*When to use: {desc}*\n" if desc else ""
            blocks.append(f"### {name}\n{desc_line}\n{content}")
        return header + "\n\n".join(blocks)
