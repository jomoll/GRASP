from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .vendor.prompts import (
    CRITIQUE_SUFFIX,
    FORMAT_RULES_OPERATION_TEMPLATE,
    HUMAN_CRITIQUE_COMPARE_TEMPLATE,
    HUMAN_CRITIQUE_SUCCESS_TEMPLATE,
    RULE_INJECTION_TEMPLATE,
    SYSTEM_CRITIQUE_COMPARE_PROMPT,
    SYSTEM_CRITIQUE_SUCCESS_PROMPT,
)
from .vendor.rules import format_rules, parse_rules, update_rules
from .vendor.store import ExperienceStore

logger = logging.getLogger(__name__)

# Cap how many success histories we concatenate into one all-success critique call
_MAX_SUCCESS_HISTORIES = 10


class ExPeLPipelineAdapter:
    """
    Orchestrates ExpeL contrastive-rule extraction for one epoch.

    Per epoch:
      1. All dev entries are added to the ExperienceStore (success / failure).
      2. For each (success, failure) pair → LLM compare-critique → parse ops.
      3. All successes → one LLM all-success critique → parse ops.
      4. update_rules() applies all collected ops → save rules + store.
    """

    def __init__(
        self,
        lm_adapter: Any,
        rules_path: Path,
        store_path: Path,
        config: Dict[str, Any],
    ) -> None:
        self.lm_adapter = lm_adapter
        self.rules_path = Path(rules_path)
        self.store_path = Path(store_path)
        self.max_num_rules: int = config.get("max_num_rules", 20)

        self.rules: List[Tuple[str, int]] = self._load_rules()
        self.store: ExperienceStore = self._load_store()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_rules(self) -> List[Tuple[str, int]]:
        if self.rules_path.exists():
            try:
                with self.rules_path.open(encoding="utf-8") as f:
                    data = json.load(f)
                return [(r["text"], r["counter"]) for r in data]
            except Exception as exc:
                logger.warning("Failed to load rules, starting fresh: %s", exc)
        return []

    def _save_rules(self) -> None:
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        with self.rules_path.open("w", encoding="utf-8") as f:
            json.dump(
                [{"text": t, "counter": c} for t, c in self.rules],
                f, ensure_ascii=False, indent=2,
            )

    def _load_store(self) -> ExperienceStore:
        if self.store_path.exists():
            try:
                return ExperienceStore.load(self.store_path)
            except Exception as exc:
                logger.warning("Failed to load experience store, starting fresh: %s", exc)
        return ExperienceStore()

    def _save_store(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store.save(self.store_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_epoch(self, dev_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add entries to store, run critique pipeline, persist, return stats."""
        for entry in dev_entries:
            is_success = bool(entry.get("is_correct")) and not entry.get("error")
            self.store.add(entry, is_success)

        stats = asyncio.run(self._extract_and_update())
        self._save_rules()
        self._save_store()
        return stats

    def build_rule_block(self) -> str:
        """Build the rule injection string for inference-time context prepending."""
        if not self.rules:
            return ""
        return RULE_INJECTION_TEMPLATE.format(rules=format_rules(self.rules))

    # ------------------------------------------------------------------
    # Internal async pipeline
    # ------------------------------------------------------------------

    async def _extract_and_update(self) -> Dict[str, Any]:
        pairs = self.store.get_compare_pairs()
        successes = self.store.get_all_successes()
        list_full = self.max_num_rules <= len(self.rules)
        existing = format_rules(self.rules)
        suffix = CRITIQUE_SUFFIX["full" if list_full else "not_full"]

        all_ops = []

        # Step A: compare critiques (one per success/failure pair)
        compare_tasks = [
            self._compare_critique(success, fail, existing, suffix)
            for success, fail in pairs
        ]
        compare_results = await asyncio.gather(*compare_tasks, return_exceptions=True)
        for r in compare_results:
            if isinstance(r, Exception):
                logger.warning("Compare critique error: %s", r)
            else:
                all_ops.extend(r)

        # Step B: all-success critique (one call, capped batch)
        if successes:
            try:
                success_ops = await self._success_critique(
                    successes[:_MAX_SUCCESS_HISTORIES], existing, suffix
                )
                all_ops.extend(success_ops)
            except Exception as exc:
                logger.warning("Success critique error: %s", exc)

        # Step C: update rules
        self.rules = update_rules(self.rules, all_ops, list_full, self.max_num_rules)

        return {
            "n_successes": len(successes),
            "n_failures": len(self.store.failures),
            "n_pairs_critiqued": len(pairs),
            "n_rules": len(self.rules),
        }

    async def _compare_critique(
        self,
        success: Dict[str, Any],
        fail: Dict[str, Any],
        existing: str,
        suffix: str,
    ) -> List[Any]:
        human = HUMAN_CRITIQUE_COMPARE_TEMPLATE.format(
            instruction=FORMAT_RULES_OPERATION_TEMPLATE,
            task=fail["instruction"],
            success_history=success["history_text"],
            fail_history=fail["history_text"],
            existing_rules=existing,
            format_ops=FORMAT_RULES_OPERATION_TEMPLATE,
            critique_suffix=suffix,
        )
        messages = [
            ("system", SYSTEM_CRITIQUE_COMPARE_PROMPT),
            ("human", human),
        ]
        try:
            response = await self.lm_adapter.ainvoke(messages)
            return parse_rules(response)
        except Exception as exc:
            logger.warning("Compare critique LLM error: %s", exc)
            return []

    async def _success_critique(
        self,
        successes: List[Dict[str, Any]],
        existing: str,
        suffix: str,
    ) -> List[Any]:
        combined = "\n\n---\n\n".join(
            f"TASK: {s['instruction']}\n\nTRAJECTORY:\n{s['history_text']}"
            for s in successes
        )
        human = HUMAN_CRITIQUE_SUCCESS_TEMPLATE.format(
            instruction=FORMAT_RULES_OPERATION_TEMPLATE,
            success_history=combined,
            existing_rules=existing,
            format_ops=FORMAT_RULES_OPERATION_TEMPLATE,
            critique_suffix=suffix,
        )
        messages = [
            ("system", SYSTEM_CRITIQUE_SUCCESS_PROMPT),
            ("human", human),
        ]
        response = await self.lm_adapter.ainvoke(messages)
        return parse_rules(response)
