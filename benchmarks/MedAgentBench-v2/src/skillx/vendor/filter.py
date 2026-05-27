# Vendored from SkillX/filtering/{base,pipeline}.py (arXiv 2604.04804).
# ToolSchemaFilter (stage 2) dropped entirely; stage 2 is always skipped here.
"""Skill quality filter — stage 1 (general) only."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from .prompts import GENERAL_FILTER_PROMPT

logger = logging.getLogger(__name__)


class GeneralFilter:
    """LLM-based general quality filter (stage 1)."""

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    async def _filter_one(self, skill: Dict[str, Any]) -> bool:
        skill_data = skill.get("skill", skill)
        content = skill_data.get("content", "")
        messages = [
            ("system", GENERAL_FILTER_PROMPT),
            ("human", f"# Here is the function: {content}"),
        ]
        try:
            response = await self.llm.ainvoke(messages=messages)
            return "good" in response.lower()
        except Exception as exc:
            logger.error("GeneralFilter error: %s", exc)
            return False

    async def filter_batch(
        self,
        skills: List[Dict[str, Any]],
        batch_size: int = 10,
        max_concurrent: int = 5,
        show_progress: bool = False,
    ) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _run(skill: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                result = skill.copy()
                result["filter_result"] = await self._filter_one(skill)
                return result

        results = await asyncio.gather(*[_run(s) for s in skills], return_exceptions=True)
        out = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error("Filter gather error: %s", r)
                item = skills[i].copy()
                item["filter_result"] = False
                out.append(item)
            else:
                out.append(r)
        return out


class TwoStageFilterPipeline:
    """Stage-1-only filter pipeline (stage 2 always skipped — no tool schemas)."""

    def __init__(
        self,
        llm: Any,
        skip_stage1: bool = False,
        skip_stage2: bool = True,
    ) -> None:
        self.general_filter = GeneralFilter(llm)
        self.skip_stage1 = skip_stage1

    async def filter(
        self,
        skills: List[Dict[str, Any]],
        batch_size: int = 10,
        max_concurrent: int = 5,
        show_progress: bool = False,
        **_kwargs: Any,
    ) -> List[Dict[str, Any]]:
        def _skill_type(s: Dict[str, Any]) -> str:
            t = s.get("skill_type")
            if not t:
                inner = s.get("skill")
                if isinstance(inner, dict):
                    t = inner.get("skill_type")
                    if not t and isinstance(inner.get("metadata"), dict):
                        t = inner["metadata"].get("skill_type")
            return t or "functional"

        functional = [s for s in skills if _skill_type(s) != "atomic"]
        atomic = [s for s in skills if _skill_type(s) == "atomic"]

        if not self.skip_stage1 and functional:
            stage1 = await self.general_filter.filter_batch(
                functional,
                batch_size=batch_size,
                max_concurrent=max_concurrent,
                show_progress=show_progress,
            )
            passed = [s for s in stage1 if s.get("filter_result", False)]
        else:
            passed = functional

        logger.info(
            "Stage 1: %d/%d functional passed; %d atomic bypassed",
            len(passed), len(functional), len(atomic),
        )
        return passed + atomic
