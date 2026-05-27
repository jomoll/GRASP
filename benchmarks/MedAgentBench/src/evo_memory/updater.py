from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.evo_memory.core import (
    EvoMemoryCore,
    _is_actionable_rule,
    _normalize_rule,
    _semantic_key,
    _truncate,
)


def _last_agent_response(entry: Dict[str, Any]) -> str:
    task_result = entry.get("task_result")
    if task_result is not None:
        return _truncate(task_result, 1200)
    for msg in reversed(entry.get("history") or []):
        if msg.get("role") in ("agent", "assistant"):
            content = str(msg.get("content", "") or "").strip()
            if content:
                return _truncate(content, 1200)
    return "(no response captured)"


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    candidates = []
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1))
    candidates.append(text)
    for candidate in candidates:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            continue
        try:
            data = json.loads(candidate[start:end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return None


class EvoMemoryUpdater:
    def __init__(self, agent: Any, core: EvoMemoryCore) -> None:
        self.agent = agent
        self.core = core

    def update_after_episode(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        reflection, raw = self._reflect(entry)
        normalized = self._normalize_reflection(reflection)

        # Determine whether to run the second LLM cheatsheet-curation call.
        do_curation = (
            self.core.config.semantic_enabled
            and bool(normalized.get("should_update_semantic", True))
            and bool(normalized.get("action_guidelines"))
        )

        # Pass should_update_semantic=False to core so _merge_candidate_rules is
        # skipped; the curated replacement is applied afterwards.
        core_reflection = dict(normalized, should_update_semantic=False) if do_curation else normalized
        update = self.core.update_from_reflection(entry, core_reflection)

        edit_log: Dict[str, Any] = {}
        if do_curation:
            current_texts = [r.get("text", "") for r in self.core.semantic]
            curated_texts, edit_log = self._update_cheatsheet_with_patch(
                current_rules=current_texts,
                candidate_rules=normalized["action_guidelines"],
                reflection=normalized,
            )
            self.core.sync_semantic_from_curated_texts(curated_texts, normalized.get("tags", []))
            self.core.save()
            update["added_rules"] = [t for t in curated_texts if t not in current_texts]
            update["semantic_size"] = len(self.core.semantic)

        return {
            "sample_id": entry.get("sample_id"),
            "is_correct": bool(entry.get("is_correct")),
            "reflection": normalized,
            "reflection_raw": _truncate(raw, 4000),
            "edit_log": edit_log,
            **update,
        }

    def _reflect(self, entry: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        task = {
            "instruction": entry.get("instruction") or entry.get("sample_id"),
            "context": entry.get("context", ""),
            "agent_response": _last_agent_response(entry),
            "is_correct": bool(entry.get("is_correct")),
            "ground_truth": entry.get("ground_truth"),
            "status": entry.get("status"),
        }
        current_rules = [r.get("text", "") for r in self.core.select_semantic_entries(
            "\n".join(str(task.get(k, "")) for k in ("instruction", "context")),
            self.core.config.semantic_top_k,
        )]
        prompt = (
            "You curate Evo-style test-time memory for an LLM agent benchmark. "
            "Review the completed episode and return JSON only. Extract reusable "
            "procedural lessons, not answer lookups. Use both successes and failures: "
            "successful traces can teach workflows; failed traces should identify the main correction.\n\n"
            "Schema:\n"
            "{\n"
            '  "episodic_summary": "<=80 words",\n'
            '  "failure_analysis": "brief reason the agent succeeded or failed",\n'
            '  "action_guidelines": ["portable rule", "..."],\n'
            '  "tags": ["keyword", "keyword"],\n'
            '  "should_store_episode": true,\n'
            '  "should_update_semantic": true\n'
            "}\n\n"
            "Rules:\n"
            "- Keep action_guidelines short, imperative, and reusable across similar tasks.\n"
            "- Do not include exact final answers, sample IDs, or hidden eval-only details as rules.\n"
            "- If no useful semantic lesson exists, use an empty action_guidelines list.\n\n"
            f"Current semantic rules:\n{json.dumps(current_rules, ensure_ascii=False, indent=2)}\n\n"
            f"Episode:\n{json.dumps(task, ensure_ascii=False, indent=2)}"
        )
        try:
            raw = self.agent.inference([{"role": "user", "content": prompt}])
            parsed = _extract_json(raw) or {}
            return parsed, raw or ""
        except Exception as exc:
            fallback = {
                "episodic_summary": f"Episode ended {'correctly' if entry.get('is_correct') else 'incorrectly'}.",
                "failure_analysis": f"Reflection failed: {type(exc).__name__}.",
                "action_guidelines": [],
                "tags": [],
                "should_store_episode": True,
                "should_update_semantic": False,
            }
            return fallback, json.dumps(fallback)

    def _update_cheatsheet_with_patch(
        self,
        current_rules: List[str],
        candidate_rules: List[str],
        reflection: Dict[str, Any],
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Second LLM call: ask the model to merge current rules with candidates into
        a curated, deduplicated list — following the Evo-MedAgent reference design."""
        payload = {
            "current_rules": current_rules,
            "candidate_rules": candidate_rules,
            "reflection": {k: reflection.get(k) for k in ("failure_analysis", "tags")},
        }
        prompt = (
            "You maintain a compact semantic cheatsheet for future episodes. "
            "Keep only reusable, high-signal rules and avoid duplicates.\n\n"
            "Update the semantic cheatsheet and return JSON only.\n\n"
            "Schema:\n"
            "{\n"
            '  "updated_rules": ["rule", "rule"],\n'
            '  "edit_log": {"added": ["rule"], "removed": ["rule"], "kept": ["rule"]}\n'
            "}\n\n"
            "Rules:\n"
            "- Keep the list compact and deduplicated.\n"
            "- Preserve strong existing rules unless a candidate is clearly better.\n"
            "- Only keep reusable strategies; discard anything answer-specific.\n\n"
            f"State:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        try:
            raw = self.agent.inference([{"role": "user", "content": prompt}])
            parsed = _extract_json(raw) or {}
            updated = parsed.get("updated_rules", [])
            if not isinstance(updated, list) or not updated:
                updated = list(current_rules) + list(candidate_rules)
            edit_log = parsed.get("edit_log", {})
            if not isinstance(edit_log, dict):
                edit_log = {}
        except Exception:
            updated = list(current_rules) + list(candidate_rules)
            edit_log = {}

        # Normalise and dedup the LLM output
        seen: set = set()
        deduped: List[str] = []
        for raw_rule in updated:
            text = _normalize_rule(str(raw_rule))
            if not _is_actionable_rule(text):
                continue
            key = _semantic_key(text)
            if key and key not in seen:
                seen.add(key)
                deduped.append(text)
        return deduped[: self.core.config.max_semantic_rules], edit_log

    def _normalize_reflection(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(reflection or {})
        out.setdefault("episodic_summary", "")
        out.setdefault("failure_analysis", "")
        out.setdefault("action_guidelines", [])
        out.setdefault("tags", [])
        out.setdefault("should_store_episode", True)
        out.setdefault("should_update_semantic", True)
        if not isinstance(out["action_guidelines"], list):
            out["action_guidelines"] = []
        if not isinstance(out["tags"], list):
            out["tags"] = []
        guidelines: List[str] = []
        seen = set()
        for raw in out["action_guidelines"]:
            text = _normalize_rule(str(raw))
            if not _is_actionable_rule(text):
                continue
            key = _semantic_key(text)
            if key in seen:
                continue
            seen.add(key)
            guidelines.append(_truncate(text, 240))
        out["action_guidelines"] = guidelines[:5]
        out["tags"] = [str(x).strip().lower() for x in out["tags"] if str(x).strip()][:10]
        out["episodic_summary"] = _truncate(out["episodic_summary"], 600)
        out["failure_analysis"] = _truncate(out["failure_analysis"], 600)
        return out
