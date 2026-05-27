from __future__ import annotations

import json
import math
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


_WORD_RE = re.compile(r"[a-z0-9]+")
_PRIORITY_RE = re.compile(r"^\s*\[(P[0-2])\]\s*(.*)$")
_MEMORY_TAG_RE = re.compile(r"</?(?:current_prompt|memory)>", re.IGNORECASE)


@dataclass
class EvoMemoryConfig:
    episodic_enabled: bool = True
    semantic_enabled: bool = True
    episodic_top_k: int = 3
    semantic_top_k: int = 8
    max_episodes: int = 500
    max_semantic_rules: int = 25
    max_context_chars: int = 6000
    semantic_context_max_chars: int = 2400
    episodic_context_max_chars: int = 2400
    utility_weight: float = 0.15
    ucb_c: float = 0.8
    p0_pinned_n: int = 2
    max_tags_per_rule: int = 10

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvoMemoryConfig":
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in (data or {}).items() if k in valid})


def _tokenize(text: str) -> List[str]:
    return _WORD_RE.findall(str(text or "").lower())


def _overlap_score(query: str, doc: str) -> float:
    q = set(_tokenize(query))
    d = set(_tokenize(doc))
    if not q or not d:
        return 0.0
    inter = len(q & d)
    return inter / math.sqrt(len(q) * len(d)) if inter else 0.0


def _truncate(text: Any, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    s = str(text or "")
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 20] + "\n...[truncated]"


def _normalize_rule(text: str) -> str:
    raw = str(text or "")
    wrapped = bool(_MEMORY_TAG_RE.search(raw))
    cleaned = _MEMORY_TAG_RE.sub("\n", raw)
    lines: List[str] = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("correction notes from past experience"):
            continue
        lines.append(re.sub(r"^\s*[-*]\s+", "", line).strip())
    if wrapped and len(lines) > 1:
        lines = [lines[-1]]
    s = re.sub(r"\s+", " ", " ".join(lines)).strip(" -\t\n")
    if not s:
        return ""
    if _PRIORITY_RE.match(s):
        return s
    return f"[P1] {s[0].upper() + s[1:]}"


def _strip_priority(text: str) -> str:
    m = _PRIORITY_RE.match(str(text or ""))
    return m.group(2).strip() if m else str(text or "").strip()


def _priority(text: str) -> int:
    m = _PRIORITY_RE.match(str(text or ""))
    if not m:
        return 1
    return {"P0": 0, "P1": 1, "P2": 2}.get(m.group(1), 1)


def _semantic_key(text: str) -> str:
    return " ".join(_tokenize(_strip_priority(text)))


def _merge_tags(*groups: Sequence[str], max_tags: int) -> List[str]:
    out: List[str] = []
    seen = set()
    for group in groups:
        for raw in group or []:
            tag = re.sub(r"\s+", "_", str(raw or "").strip().lower())
            if not tag or tag in seen:
                continue
            seen.add(tag)
            out.append(tag)
            if len(out) >= max_tags:
                return out
    return out


def _infer_tags(text: str, max_tags: int) -> List[str]:
    tags = []
    seen = set()
    for tok in _tokenize(text):
        if len(tok) < 4 or tok in seen:
            continue
        seen.add(tok)
        tags.append(tok)
        if len(tags) >= max_tags:
            break
    return tags


def _is_actionable_rule(text: str) -> bool:
    body = _strip_priority(_normalize_rule(text))
    if len(body) < 12:
        return False
    bad = ("the answer is", "correct answer", "option ", "sample id", "task id")
    return not any(x in body.lower() for x in bad)


class EvoMemoryCore:
    def __init__(self, root_dir: Path, config: Dict[str, Any]) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.config = EvoMemoryConfig.from_dict(config)
        self.episodic_path = self.root_dir / "episodic.jsonl"
        self.semantic_path = self.root_dir / "semantic.json"
        self.episodic: List[Dict[str, Any]] = self._load_episodic()
        self.semantic: List[Dict[str, Any]] = self._load_semantic()

    def build_context(self, query: str) -> str:
        q = _truncate(query, 3000)
        parts = [
            "## Evo Memory-Guided Reasoning Protocol\n"
            "- Use memory as strategy guidance, not as answer lookup.\n"
            "- Prefer current task details over remembered details.\n"
            "- Reuse portable workflows and avoid copying prior final answers."
        ]
        rules = self.select_semantic_entries(q, self.config.semantic_top_k)
        if self.config.semantic_enabled and rules:
            lines = [f"- {r['text']}" for r in rules]
            parts.append(_truncate(
                "## Dynamic Cheatsheet (semantic memory)\n" + "\n".join(lines),
                self.config.semantic_context_max_chars,
            ))
        episodes = self.retrieve_similar_episodes(q, self.config.episodic_top_k)
        if self.config.episodic_enabled and episodes:
            lines: List[str] = []
            for i, rec in enumerate(episodes, start=1):
                summary = rec.get("episodic_summary", "")
                if summary:
                    lines.append(f"- Similar episode {i}: {summary}")
                for rule in (rec.get("action_guidelines") or [])[:2]:
                    lines.append(f"  - {_strip_priority(str(rule))}")
            parts.append(_truncate(
                "## Similar Past Episodes (episodic memory)\n" + "\n".join(lines),
                self.config.episodic_context_max_chars,
            ))
        return _truncate("\n\n".join(p for p in parts if p).strip(), self.config.max_context_chars)

    def select_semantic_entries(self, query: str, max_rules: Optional[int] = None) -> List[Dict[str, Any]]:
        if not self.semantic:
            return []
        limit = min(max_rules or self.config.semantic_top_k, self.config.max_semantic_rules)
        total_shown = sum(int(e.get("shown", 0) or 0) for e in self.semantic)
        scored: List[Tuple[Tuple[float, float, float], Dict[str, Any]]] = []
        for entry in self.semantic:
            text = str(entry.get("text", ""))
            tags = " ".join(entry.get("tags", []) or [])
            relevance = _overlap_score(query, text + " " + tags)
            utility = self._ucb(entry, total_shown)
            priority_bonus = 2.0 - float(_priority(text))
            scored.append(((priority_bonus, relevance + self.config.utility_weight * utility, utility), entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        pinned = [e for _, e in scored if _priority(str(e.get("text", ""))) == 0][: self.config.p0_pinned_n]
        chosen: List[Dict[str, Any]] = []
        seen = set()
        for entry in pinned + [e for _, e in scored]:
            rid = str(entry.get("id", ""))
            if rid in seen:
                continue
            seen.add(rid)
            chosen.append(entry)
            if len(chosen) >= limit:
                break
        return chosen

    def retrieve_similar_episodes(self, query: str, k: int) -> List[Dict[str, Any]]:
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for rec in self.episodic:
            doc = " ".join([
                str(rec.get("task", "")),
                str(rec.get("episodic_summary", "")),
                str(rec.get("failure_analysis", "")),
                " ".join(rec.get("action_guidelines") or []),
                " ".join(rec.get("tags") or []),
            ])
            score = _overlap_score(query, doc)
            if score > 0:
                scored.append((score, rec))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [rec for _, rec in scored[: max(0, int(k))]]

    def update_from_reflection(self, entry: Dict[str, Any], reflection: Dict[str, Any]) -> Dict[str, Any]:
        shown = self.select_semantic_entries(self._entry_query(entry), self.config.semantic_top_k)
        self._credit_rules(shown, bool(entry.get("is_correct")), reflection)

        stored_episode = None
        if self.config.episodic_enabled and reflection.get("should_store_episode", True):
            stored_episode = self._append_episode(entry, reflection)

        added_rules: List[str] = []
        if self.config.semantic_enabled and reflection.get("should_update_semantic", True):
            added_rules = self._merge_candidate_rules(reflection.get("action_guidelines") or [], reflection.get("tags") or [])

        self.save()
        return {
            "stored_episode_id": stored_episode.get("id") if stored_episode else None,
            "shown_rule_ids": [r.get("id") for r in shown],
            "added_rules": added_rules,
            "semantic_size": len(self.semantic),
            "episodic_size": len(self.episodic),
        }

    def sync_semantic_from_curated_texts(self, curated_texts: List[str], tags: List[str]) -> None:
        """Replace semantic memory with an LLM-curated list, preserving stats for surviving rules."""
        old_by_key = {_semantic_key(e.get("text", "")): e for e in self.semantic}
        merged: List[Dict[str, Any]] = []
        seen: set = set()
        for raw in curated_texts:
            text = _normalize_rule(str(raw))
            if not _is_actionable_rule(text):
                continue
            key = _semantic_key(text)
            if not key or key in seen:
                continue
            seen.add(key)
            if key in old_by_key:
                entry = dict(old_by_key[key])
                entry["text"] = text
                entry["tags"] = _merge_tags(
                    entry.get("tags", []), tags,
                    _infer_tags(text, self.config.max_tags_per_rule),
                    max_tags=self.config.max_tags_per_rule,
                )
                entry["updated_at"] = datetime.now().isoformat()
            else:
                entry = {
                    "id": f"rule_{uuid.uuid4().hex[:12]}",
                    "text": text,
                    "tags": _merge_tags(tags, _infer_tags(text, self.config.max_tags_per_rule), max_tags=self.config.max_tags_per_rule),
                    "shown": 0,
                    "success": 0,
                    "failure": 0,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            merged.append(entry)
        self.semantic = self._postprocess_semantic(merged)

    def save(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        with self.episodic_path.open("w", encoding="utf-8") as f:
            for rec in self.episodic[-self.config.max_episodes:]:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(),
            "rules": [e["text"] for e in self.semantic],
            "rule_entries": self.semantic,
        }
        self.semantic_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def snapshot_to(self, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        self.save()
        for path in (self.episodic_path, self.semantic_path):
            if path.exists():
                target = dst / path.name
                target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    def _entry_query(self, entry: Dict[str, Any]) -> str:
        return "\n".join([
            str(entry.get("instruction", "")),
            str(entry.get("context", "")),
            str(entry.get("task_result", "")),
        ])

    def _append_episode(self, entry: Dict[str, Any], reflection: Dict[str, Any]) -> Dict[str, Any]:
        rec = {
            "id": f"epi_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now().isoformat(),
            "sample_id": entry.get("sample_id"),
            "task": _truncate(self._entry_query(entry), 1200),
            "is_correct": bool(entry.get("is_correct")),
            "ground_truth": _truncate(entry.get("ground_truth"), 800),
            "episodic_summary": _truncate(reflection.get("episodic_summary"), 600),
            "failure_analysis": _truncate(reflection.get("failure_analysis"), 600),
            "action_guidelines": [str(x) for x in reflection.get("action_guidelines", [])][:5],
            "tags": _merge_tags(reflection.get("tags", []), max_tags=self.config.max_tags_per_rule),
        }
        self.episodic.append(rec)
        if len(self.episodic) > self.config.max_episodes:
            self.episodic = self.episodic[-self.config.max_episodes:]
        return rec

    def _merge_candidate_rules(self, rules: Sequence[str], tags: Sequence[str]) -> List[str]:
        existing_by_key = {_semantic_key(e.get("text", "")): e for e in self.semantic}
        added: List[str] = []
        for raw in rules:
            text = _normalize_rule(str(raw))
            if not _is_actionable_rule(text):
                continue
            key = _semantic_key(text)
            if not key:
                continue
            if key in existing_by_key:
                entry = existing_by_key[key]
                entry["tags"] = _merge_tags(entry.get("tags", []), tags, _infer_tags(text, self.config.max_tags_per_rule), max_tags=self.config.max_tags_per_rule)
                entry["updated_at"] = datetime.now().isoformat()
                continue
            entry = {
                "id": f"rule_{uuid.uuid4().hex[:12]}",
                "text": text,
                "tags": _merge_tags(tags, _infer_tags(text, self.config.max_tags_per_rule), max_tags=self.config.max_tags_per_rule),
                "shown": 0,
                "success": 0,
                "failure": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            self.semantic.append(entry)
            existing_by_key[key] = entry
            added.append(text)
        self.semantic = self._postprocess_semantic(self.semantic)
        return added

    def _credit_rules(self, shown: List[Dict[str, Any]], was_correct: bool, reflection: Dict[str, Any]) -> None:
        if not shown:
            return
        failure_text = str(reflection.get("failure_analysis", ""))
        tags_text = " ".join(reflection.get("tags", []) or [])
        for shown_entry in shown:
            rid = shown_entry.get("id")
            entry = next((e for e in self.semantic if e.get("id") == rid), None)
            if not entry:
                continue
            rel = max(
                _overlap_score(failure_text, str(entry.get("text", ""))),
                _overlap_score(tags_text, " ".join(entry.get("tags", []) or [])),
            )
            entry["shown"] = int(entry.get("shown", 0) or 0) + 1
            if was_correct:
                entry["success"] = int(entry.get("success", 0) or 0) + 1
            elif rel > 0:
                entry["failure"] = int(entry.get("failure", 0) or 0) + 1
            entry["updated_at"] = datetime.now().isoformat()

    def _ucb(self, entry: Dict[str, Any], total_shown: int) -> float:
        shown = max(0, int(entry.get("shown", 0) or 0))
        success = max(0, int(entry.get("success", 0) or 0))
        if shown == 0:
            return 1.0
        mean = success / max(1, shown)
        return mean + self.config.ucb_c * math.sqrt(math.log(max(2, total_shown + 1)) / shown)

    def _postprocess_semantic(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clean: List[Dict[str, Any]] = []
        seen = set()
        for entry in entries:
            text = _normalize_rule(str(entry.get("text", "")))
            if not _is_actionable_rule(text):
                continue
            key = _semantic_key(text)
            if key in seen:
                continue
            seen.add(key)
            item = dict(entry)
            item["text"] = text
            item["tags"] = _merge_tags(item.get("tags", []), _infer_tags(text, self.config.max_tags_per_rule), max_tags=self.config.max_tags_per_rule)
            clean.append(item)
        total = sum(int(e.get("shown", 0) or 0) for e in clean) or 1
        clean.sort(key=lambda e: (_priority(str(e.get("text", ""))), -self._ucb(e, total), str(e.get("text", ""))))
        return clean[: self.config.max_semantic_rules]

    def _load_episodic(self) -> List[Dict[str, Any]]:
        if not self.episodic_path.exists():
            return []
        out = []
        with self.episodic_path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return out[-self.config.max_episodes:]

    def _load_semantic(self) -> List[Dict[str, Any]]:
        if not self.semantic_path.exists():
            return []
        try:
            data = json.loads(self.semantic_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        raw = data.get("rule_entries", []) if isinstance(data, dict) else []
        if not raw and isinstance(data, dict):
            raw = [{"text": r} for r in data.get("rules", []) or []]
        return self._postprocess_semantic([r for r in raw if isinstance(r, dict)])


__all__ = ["EvoMemoryCore", "EvoMemoryConfig", "_truncate"]
