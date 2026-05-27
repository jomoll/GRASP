# Vendored from SkillX/clustering/merger.py (arXiv 2604.04804).
# Functional-only; atomic tool_schemas handling and ToolSchemaRegistry dropped.
"""LLM-based skill merging for same-name duplicates."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional

from .prompts import FUNCTIONAL_MERGE_PROMPT

logger = logging.getLogger(__name__)


class SkillMerger:
    """Merge clusters of same-name skills using an LLM."""

    def __init__(self, llm: Any, max_group_size: int = 15) -> None:
        self.llm = llm
        self.max_group_size = max_group_size

    def _extract_skill(self, text: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"<skill>(.*?)</skill>", text, flags=re.S)
        if match:
            raw = match.group(1).strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                try:
                    result = eval(raw)  # noqa: S307
                    if isinstance(result, list) and result:
                        return result[0] if len(result) == 1 else result
                    return result
                except Exception:
                    pass
        return None

    async def merge(self, skills: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if len(skills) == 1:
            return skills[0]

        if len(skills) > self.max_group_size:
            skills = random.sample(skills, self.max_group_size)

        skill_list = [
            json.dumps(s.get("skill", s), ensure_ascii=False, indent=2)
            for s in skills
        ]
        messages = [
            ("system", FUNCTIONAL_MERGE_PROMPT),
            ("human", f"# Skill List:\n{skill_list}"),
        ]

        try:
            response = await self.llm.ainvoke(messages=messages)
            merged = self._extract_skill(response)
            if merged:
                return {
                    "skill": merged,
                    "source": skills,
                    "merged_from_count": len(skills),
                }
        except Exception as exc:
            logger.error("SkillMerger error: %s", exc)

        return None

    async def merge_clusters(
        self, clusters: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        tasks = [self.merge(c) for c in clusters]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = []
        for r in results:
            if isinstance(r, Exception):
                logger.error("Merge cluster error: %s", r)
            elif r:
                out.append(r)
        logger.info("Merged %d clusters → %d skills", len(clusters), len(out))
        return out
