# Vendored from SkillX/extraction/{plan,skill}_extractor.py (arXiv 2604.04804).
# Stripped to PlanExtractor + FunctionalSkillExtractor only; no abstract base hierarchy.
"""Plan and functional-skill extraction from agent trajectories."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .prompts import PLAN_EXTRACTION_PROMPT, FUNCTIONAL_SKILL_PROMPT

logger = logging.getLogger(__name__)


class PlanExtractor:
    """Extract a reusable plan from a successful trajectory."""

    def __init__(self, llm: Any, max_retries: int = 5) -> None:
        self.llm = llm
        self.max_retries = max_retries

    def _extract_plan(self, text: str) -> Optional[str]:
        match = re.search(r"<plan>(.*?)</plan>", text, flags=re.S)
        if match:
            return match.group(1).strip()
        return None

    async def extract(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user_task = (
            item.get("user_task")
            or item.get("task")
            or item.get("query")
            or item.get("instruction")
            or item.get("goal")
            or ""
        )
        trajectory = item.get("task_history", item.get("trajectory", []))

        messages = [
            ("system", PLAN_EXTRACTION_PROMPT),
            ("human", f"user task: {user_task}\n\nan agent's interaction history: {trajectory}"),
        ]

        try:
            response = await self.llm.ainvoke(messages=messages)
            plan = self._extract_plan(response)
            if plan:
                result = item.copy()
                result["plan"] = plan
                result.setdefault("user_task", user_task)
                return result
        except Exception as exc:
            logger.error("PlanExtractor error: %s", exc)

        return None


class FunctionalSkillExtractor:
    """Extract functional skills per plan step from a successful trajectory."""

    def __init__(self, llm: Any, max_retries: int = 5) -> None:
        self.llm = llm
        self.max_retries = max_retries

    def _extract_skills(self, text: str) -> Optional[List[Dict[str, Any]]]:
        # Try ```json ... ```
        m = re.search(r"```json(.*?)```", text, flags=re.S)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass
        # Try ``` ... ```
        m = re.search(r"```(.*?)```", text, flags=re.S)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass
        # Try raw JSON array
        m = re.search(r"\[\s*\{.*?\}\s*\]", text, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None

    async def extract(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user_task = item.get("user_task", "")
        successful_trajectory = item.get("successful_trajectory", item.get("trajectory", []))
        plan = item.get("plan", "")
        exp_metadata = item.get("exp_metadata", {})
        skill_library: List = (
            exp_metadata.get("skills", []) if isinstance(exp_metadata, dict) else []
        )

        # Parse plan steps: split by "#", keep steps containing "api"
        raw_steps = plan.split("#")
        plan_steps = [
            s.strip() for s in raw_steps
            if len(s.strip()) >= 5 and "api" in s.lower()
        ]
        if not plan_steps:
            plan_steps = [
                line.strip()
                for line in plan.split("\n")
                if line.strip().startswith("#")
            ]
        if not plan_steps:
            logger.warning("No plan steps found; skipping extraction")
            return None

        plan_step_metadata: Dict[str, Any] = {}

        for step in plan_steps:
            messages = [
                ("system", FUNCTIONAL_SKILL_PROMPT),
                ("human", (
                    f"# User task: {user_task}\n\n"
                    f"# A Successful Trajectory: {successful_trajectory}\n\n"
                    f"# Skill Library: {skill_library}\n\n"
                    f"# Specific step: {step}"
                )),
            ]

            for attempt in range(self.max_retries):
                try:
                    response = await self.llm.ainvoke(messages=messages)
                    skills = self._extract_skills(response)
                    if skills:
                        plan_step_metadata[step] = skills
                        for skill_item in skills:
                            if skill_item.get("option") in ("add", "modify"):
                                if "skill" in skill_item:
                                    skill_library.append(skill_item["skill"])
                        break
                except Exception as exc:
                    logger.error(
                        "Skill extraction error (attempt %d/%d): %s",
                        attempt + 1, self.max_retries, exc,
                    )

        result = item.copy()
        result["plan_step_metadata"] = plan_step_metadata
        return result
