"""
MemoryUpdater — generates per-sample correction notes from failing agent traces
and manages the memory file (memory.json).

Prompt design matches the original MedAgentBench-v2 paper (Appendix A.2):
  - One LLM call per failing sample
  - Includes task description, agent response, eval output (ref_sol), and current memory
  - Output is plain prose starting with "when asked ..."
  - No JSON array; bullets are appended as plain strings

The memory is a flat JSON list of strings. After each update cycle:
  1. propose() calls the LLM once per failing entry.
  2. New bullets are appended to the list.

Memory is intentionally append-only to match the original MedAgentBench-v2
implementation, which grows the <memory> block without summarising it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


_WRAPPER_TAG_RE = re.compile(r"</?(?:current_prompt|memory)>", re.IGNORECASE)
_FENCED_BLOCK_RE = re.compile(r"```(?:json|text)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _strip_code_fence(text: str) -> str:
    fenced = _FENCED_BLOCK_RE.search(text)
    return fenced.group(1).strip() if fenced else text.strip()


def _normalise_memory_note(text: Any) -> Optional[str]:
    """Return one plain memory note, or None if the response is unusable."""
    if text is None:
        return None
    raw = _strip_code_fence(str(text)).strip()
    if not raw:
        return None

    # Some models return a JSON array despite the prompt. Prefer the last note,
    # which is usually the newly proposed one when the whole memory is echoed.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            notes = [_normalise_memory_note(item) for item in parsed]
            notes = [note for note in notes if note]
            return notes[-1] if notes else None
    except Exception:
        pass

    cleaned = _WRAPPER_TAG_RE.sub("\n", raw)
    lines = []
    for line in cleaned.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("correction notes from past experience"):
            continue
        line = re.sub(r"^\s*[-*]\s+", "", line).strip()
        if line:
            lines.append(line)

    if not lines:
        return None

    starts = [i for i, line in enumerate(lines) if line.lower().startswith("when asked")]
    if starts:
        start = starts[-1]
        end = next(
            (i for i in range(start + 1, len(lines)) if lines[i].lower().startswith("when asked")),
            len(lines),
        )
        note = " ".join(lines[start:end]).strip()
    else:
        match = re.search(r"\bwhen asked\b.*", " ".join(lines), re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        note = match.group(0).strip()

    note = re.sub(r"\s+", " ", note).strip()
    note = re.sub(r"^\s*[-*]\s+", "", note).strip()
    if _WRAPPER_TAG_RE.search(note) or not note.lower().startswith("when asked"):
        return None
    return note


def _normalise_memory_list(bullets: List[Any]) -> List[str]:
    normalised: List[str] = []
    seen = set()
    for bullet in bullets:
        note = _normalise_memory_note(bullet)
        if not note:
            continue
        key = note.lower()
        if key in seen:
            continue
        seen.add(key)
        normalised.append(note)
    return normalised


def _render_memory_block(bullets: List[str]) -> str:
    if not bullets:
        return "<memory>\n</memory>"
    lines = ["<memory>", "Correction notes from past experience:"]
    lines += [f"- {b}" for b in bullets]
    lines.append("</memory>")
    return "\n".join(lines)


def _format_agent_response(entry: Dict) -> str:
    task_result = entry.get("task_result")
    if task_result is not None:
        return str(task_result)[:1000]
    history = entry.get("history") or []
    for msg in reversed(history):
        if msg.get("role") in ("agent", "assistant"):
            content = str(msg.get("content", "") or "").strip()
            if content:
                return content[:1000]
    return "(no response captured)"


def _format_eval_output(entry: Dict) -> str:
    ground_truth = entry.get("ground_truth")
    is_correct = entry.get("is_correct", False)
    parts = []
    if ground_truth is not None:
        parts.append(f"ref_sol: {ground_truth}")
    parts.append(str(is_correct))
    return "\n".join(parts)


class MemoryUpdater:
    def __init__(self, agent, max_bullets: int = 20) -> None:
        self.agent = agent
        self.max_bullets = max_bullets

    def propose_one(self, entry: Dict, current_bullets: List[str]) -> Optional[str]:
        """Generate a single memory note for one failing sample (paper-style prompt)."""
        instruction = str(entry.get("instruction", "") or entry.get("sample_id", ""))
        context = str(entry.get("context", "") or "")
        task_descr = f"Instruction:\n{instruction}"
        if context:
            task_descr += f"\nContext:\n{context}"

        agent_response = _format_agent_response(entry)
        eval_output = _format_eval_output(entry)
        current_prompt = _render_memory_block(current_bullets)

        prompt = (
            "Add memory to the current_prompt. Since the current agent doesn't handle this task "
            "correctly, write instructions for a correct approach to the agent's memory so when it "
            "sees the task again, it gets it right. Think about the task description, the agent's "
            "previous response, and what the evaluation function tests to figure out why the agent "
            "got the wrong response. Use 1-3 sentences to correct its MAIN mistake. "
            "Start with \"when asked...\"\n\n"
            "Example Response: when asked \"If low, then order replacement IV magnesium according "
            "to dosing instructions.\", low indicates a value below 1.5 mg/dL.\n\n"
            f"<task_description>\n{task_descr}\n</task_description>\n\n"
            f"<agent_response>\n{agent_response}\n</agent_response>\n\n"
            f"<eval_output>\n{eval_output}\n</eval_output>\n\n"
            f"<current_prompt>\n{current_prompt}\n</current_prompt>"
        )

        try:
            response = self.agent.inference([{"role": "user", "content": prompt}])
            bullet = _normalise_memory_note(response)
            if bullet:
                print(f"[MemoryUpdater] new note: {bullet[:120]}")
                return bullet
            print("[MemoryUpdater] discarded malformed note")
        except Exception as e:
            print(f"[MemoryUpdater] propose_one failed: {e}")
        return None

    def propose(self, failing_entries: List[Dict], current_bullets: List[str]) -> List[str]:
        """Call the LLM once per failing entry to generate correction notes."""
        if not failing_entries:
            return []
        new_bullets: List[str] = []
        for entry in failing_entries:
            bullet = self.propose_one(entry, current_bullets + new_bullets)
            if bullet:
                new_bullets.append(bullet)
        return new_bullets

    def update(self, memory_path: Path, failing_entries: List[Dict]) -> List[str]:
        """Load memory, propose new notes, append, save and return updated list."""
        current: List[str] = []
        if memory_path.exists():
            try:
                current = _normalise_memory_list(
                    json.loads(memory_path.read_text(encoding="utf-8"))
                )
            except Exception:
                current = []

        new_bullets = self.propose(failing_entries, current)
        updated = current + new_bullets

        memory_path.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return updated
