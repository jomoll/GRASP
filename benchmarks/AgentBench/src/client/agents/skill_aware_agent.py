"""
SkillAwareAgent — wraps any AgentClient and injects the current skill library
into the conversation history before each inference call.

Injection strategy depends on whether this is the first agent decision or a
continuation turn:

  First decision (no prior assistant/agent turn in history):
      Skills are PREPENDED to the last user message so the model reads them
      before the task instruction.  This interrupts reflexive first-action
      behaviour that would otherwise fire before any skill context is processed.

  Continuation turn (prior assistant/agent turn exists):
      Skills are APPENDED to the last user message (after the latest environment
      observation) so they remain at the recency-favoured end of the context,
      close to the generation point.

Each skill is introduced by its description so the model can judge applicability
at a glance; the full content follows for when the skill is relevant.

The model is told once, at the top of the block, to apply skills that match and
ignore the rest — no per-skill checklists.

Skills named "skeleton" (the read-only base template) are never injected.
If no skills exist and the task is not DBBench, history is passed through unchanged.

Skill selection:
  Skills are ranked against the current conversation context using tags,
  descriptions, names, and the "When to Use" section. Tagged skills with no
  direct tag hit are still eligible; they just rank below stronger matches.
"""

import logging
import re
from typing import Any, Dict, List

from ..agent import AgentClient
from src.skills.repository import SkillRepository

logger = logging.getLogger(__name__)

# Maximum skills injected per turn across all benchmarks.
_MAX_SKILLS = 3

_STOPWORDS = {
    "a", "an", "and", "are", "as", "be", "by", "for", "from", "has", "have",
    "i", "if", "in", "into", "is", "it", "me", "my", "of", "on", "or",
    "the", "then", "this", "to", "use", "was", "when", "with", "you", "your",
}


class SkillAwareAgent(AgentClient):
    def __init__(self, agent: AgentClient, skill_repo: SkillRepository) -> None:
        super().__init__()
        self.agent = agent
        self.skill_repo = skill_repo

    def inference(self, history: List[dict], tools=None):
        skills = [s for s in self.skill_repo.load_all() if s["name"] != "skeleton"]
        first_content = self._message_content(history[0]) if history else ""
        selection_context = self._selection_context(history)
        is_dbbench = self._is_dbbench_prompt(first_content)

        skills = self._select_skills(skills, selection_context)

        if not skills and not is_dbbench:
            return self._delegate(history, tools=tools)

        suffix_parts = []
        if skills:
            suffix_parts.append(self._render_skills(skills))
        if is_dbbench:
            suffix_parts.append(self._dbbench_protocol())

        skill_block = "\n\n" + "\n\n".join(suffix_parts)

        modified = [self._message_to_dict(message) for message in history]
        last_user_idx = max(
            (
                i for i, m in enumerate(modified)
                if m.get("role") in ("user", "system")
            ),
            default=0,
        )

        # Determine injection position based on whether the agent has already
        # taken at least one turn.  "agent" covers DBBench's acknowledgement
        # message; "assistant" covers standard chat-format tasks.
        is_first_decision = not any(
            m.get("role") in ("assistant", "agent")
            for m in modified[:last_user_idx + 1]
        )

        if is_first_decision:
            # Prepend: skills appear before the task instruction so the model
            # processes behavioural rules before reading the task and acting.
            new_content = (
                skill_block.lstrip("\n")
                + "\n\n"
                + (modified[last_user_idx].get("content") or "")
            )
        else:
            # Append: skills stay at the recency-favoured end of the context,
            # immediately before generation on continuation turns.
            new_content = (modified[last_user_idx].get("content") or "") + skill_block

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

    @classmethod
    def _message_content(cls, message: Any) -> str:
        item = cls._message_to_dict(message)
        content = item.get("content") or ""
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    parts.append(str(part.get("text", "")))
                else:
                    parts.append(str(part))
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _render_skills(skills: list) -> str:
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

    @classmethod
    def _selection_context(cls, history: List[dict]) -> str:
        """Build a compact text view of the task and recent observations."""
        parts = []
        for message in history:
            content = cls._message_content(message)
            if content:
                parts.append(content)
        return "\n".join(parts)[-12000:]

    @staticmethod
    def _tokens(text: str) -> set:
        return {
            token for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 2 and token not in _STOPWORDS
        }

    @staticmethod
    def _tag_terms(tag: str) -> List[str]:
        return [
            part for part in re.split(r"[^a-z0-9]+", tag.lower())
            if len(part) > 2 and part not in _STOPWORDS
        ]

    @staticmethod
    def _when_to_use(content: str) -> str:
        match = re.search(
            r"(?is)##+\s*when to use(?: this skill)?\s*(.*?)(?=\n##+\s|\Z)",
            content or "",
        )
        return match.group(1) if match else ""

    @classmethod
    def _select_skills(cls, skills: List[Dict], task_text: str) -> List[Dict]:
        """Return at most _MAX_SKILLS skills ranked by relevance.

        Tags get the strongest weight, but names, descriptions, and "When to Use"
        text provide a fallback when older skills have technical tags such as
        ``numeric_extraction`` that do not appear verbatim in user tasks.
        """
        task_lower = task_text.lower()
        task_tokens = cls._tokens(task_text)
        ranked: List[tuple] = []

        for order, skill in enumerate(skills):
            tags = [t.lower() for t in (skill.get("tags") or [])]
            tag_score = 0
            for tag in tags:
                terms = cls._tag_terms(tag)
                if not terms:
                    continue
                if re.search(r"\b" + re.escape(tag) + r"\b", task_lower):
                    tag_score += 3
                elif all(term in task_tokens for term in terms):
                    tag_score += 2
                else:
                    tag_score += sum(1 for term in terms if term in task_tokens)

            selector_text = " ".join(
                [
                    skill.get("name", "").replace("_", " "),
                    skill.get("description", ""),
                    cls._when_to_use(skill.get("content", "")),
                ]
            )
            selector_tokens = cls._tokens(selector_text)
            text_score = len(task_tokens & selector_tokens)
            score = tag_score * 10 + text_score

            # Untagged skills are intentionally general, but should not beat a
            # concrete tagged match.  Give them a small stable floor.
            if not tags:
                score += 1

            ranked.append((-score, order, skill))

        ranked.sort(key=lambda x: (x[0], x[1]))
        selected = [s for _, _, s in ranked[:_MAX_SKILLS]]

        logger.info(
            "skill_selection selected=%s scores=%s",
            [s["name"] for s in selected],
            {skill["name"]: -score for score, _, skill in ranked},
        )
        return selected

    @classmethod
    def _is_dbbench_prompt(cls, content: str) -> bool:
        if not isinstance(content, str):
            return False
        text = content.lower()
        return (
            "help me operate a mysql database with sql" in text
            or "execute_sql" in text
            or "commit_final_answer" in text
        )

    @staticmethod
    def _dbbench_protocol() -> str:
        return (
            "---\n"
            "**SQL tool reminder:** use the provided DBBench tools; do not write "
            "tool invocations as plain text.\n"
            "- Query or mutate the database with `execute_sql`.\n"
            "- Submit the answer with `commit_final_answer` only when done.\n"
            "- For INSERT/UPDATE/DELETE tasks, verify the changed rows with a "
            "targeted SELECT before submitting."
        )
