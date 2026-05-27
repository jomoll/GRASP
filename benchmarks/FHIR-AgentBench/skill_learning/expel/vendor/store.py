# Adapted from ExpeL/memory/episode.py (arXiv 2308.10144).
# Simplified: no FAISS, no embeddings — BM25 overlap for nearest-success matching.
"""Experience store for ExpeL contrastive rule extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _bm25_overlap(q: str, d: str) -> float:
    """Jaccard overlap on lowercased tokens — same as SkillX agent.py retrieval."""
    qs = set(_tokenize(q))
    ds = set(_tokenize(d))
    if not qs or not ds:
        return 0.0
    return len(qs & ds) / len(qs | ds)


def _history_to_text(history: List[Dict]) -> str:
    """Render a message history list as a readable string."""
    parts = []
    for m in history:
        role = m.get("role", "")
        content = str(m.get("content", ""))
        parts.append(f"{role.upper()}: {content}")
    return "\n".join(parts)


class ExperienceStore:
    """Stores successful and failed trajectories; pairs them for ExpeL critique."""

    def __init__(self) -> None:
        self.successes: List[Dict] = []  # [{task_id, instruction, history_text}]
        self.failures: List[Dict] = []   # [{task_id, instruction, history_text}]

    def add(self, entry: Dict, is_success: bool) -> None:
        instruction = entry.get("instruction") or entry.get("sample_id") or ""
        history = entry.get("history") or []
        record = {
            "task_id": entry.get("sample_id", ""),
            "instruction": instruction,
            "history_text": _history_to_text(history),
        }
        if is_success:
            self.successes.append(record)
        else:
            self.failures.append(record)

    def get_compare_pairs(self) -> List[Tuple[Dict, Dict]]:
        """For each failure, find the nearest success by BM25 on instruction text."""
        if not self.successes or not self.failures:
            return []
        pairs = []
        for fail in self.failures:
            scored = [
                (_bm25_overlap(fail["instruction"], s["instruction"]), s)
                for s in self.successes
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            best_success = scored[0][1]
            pairs.append((best_success, fail))
        return pairs

    def get_all_successes(self) -> List[Dict]:
        return list(self.successes)

    def to_dict(self) -> Dict:
        return {"successes": self.successes, "failures": self.failures}

    def save(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "ExperienceStore":
        store = cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        store.successes = data.get("successes", [])
        store.failures = data.get("failures", [])
        return store
