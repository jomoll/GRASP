# Vendored from ExpeL/agent/expel.py (arXiv 2308.10144), lines 665-743.
# parse_rules, update_rules, format_rules — pure functions, no external deps.
"""Rule parsing and update logic for ExpeL contrastive rule extraction."""

from __future__ import annotations

import re
from typing import List, Tuple

PARSE_PATTERN = re.compile(
    r"((?:REMOVE|EDIT|ADD|AGREE)(?: \d+|)): (?:[a-zA-Z\s\d]+: |)(.*)"
)
BANNED_KEYWORDS = ["ADD", "AGREE", "EDIT"]


def parse_rules(text: str) -> List[Tuple[str, str]]:
    """Parse LLM output into (operation, rule_text) pairs.

    Filters out empty rules, rules containing banned keywords, and rules that
    do not end with a period (verbatim logic from ExpeL expel.py:665-681).
    """
    ops: List[Tuple[str, str]] = []
    for match in PARSE_PATTERN.finditer(text):
        op_raw, rule_text = match.group(1), match.group(2).strip()
        if not rule_text:
            continue
        if any(kw in rule_text for kw in BANNED_KEYWORDS):
            continue
        if not rule_text.endswith("."):
            rule_text += "."
        op = "ADD" if "ADD" in op_raw else op_raw.strip()
        ops.append((op, rule_text))
    return ops


def _rule_number_in_text(rule_text: str, idx: int) -> bool:
    """Return True if the 1-based rule index appears in the operation text."""
    return str(idx + 1) in rule_text


def _find_rule_index(rules: List[Tuple[str, int]], op_text: str) -> int:
    """Return the 0-based index of the rule referenced in op_text, or -1."""
    for i, (_, _) in enumerate(rules):
        if str(i + 1) in op_text:
            return i
    return -1


def update_rules(
    rules: List[Tuple[str, int]],
    operations: List[Tuple[str, str]],
    list_full: bool,
    max_num_rules: int = 20,
) -> List[Tuple[str, int]]:
    """Apply AGREE/REMOVE/EDIT/ADD operations to the rule list.

    Counter values verbatim from ExpeL expel.py lines 696-743:
      REMOVE: -1 (or -3 when list_full)
      AGREE:  +1
      EDIT:   +1, text updated
      ADD:    +2, new entry appended

    Rules with counter <= 0 are dropped; survivors sorted descending by counter.
    """
    rules = [list(r) for r in rules]  # make mutable: [[text, counter], ...]

    # Pre-filter invalid operations (verbatim logic from expel.py:697-719)
    valid_ops: List[Tuple[str, str]] = []
    for op, text in operations:
        if op == "ADD":
            # Skip if the text already exists as a rule
            if any(text == r[0] for r in rules):
                continue
        elif op == "EDIT":
            idx = _find_rule_index(rules, text)  # type: ignore[arg-type]
            if idx == -1 or idx >= len(rules):
                continue
            # Convert to AGREE if text unchanged
            if text == rules[idx][0]:
                op = "AGREE"
        elif op in ("REMOVE", "AGREE"):
            idx = _find_rule_index(rules, text)  # type: ignore[arg-type]
            if idx == -1:
                continue
        valid_ops.append((op, text))

    # Apply operations in ExpeL order: REMOVE → AGREE → EDIT → ADD
    for order_op in ("REMOVE", "AGREE", "EDIT", "ADD"):
        for op, text in valid_ops:
            if op != order_op:
                continue
            if op == "REMOVE":
                idx = _find_rule_index(rules, text)  # type: ignore[arg-type]
                if 0 <= idx < len(rules):
                    rules[idx][1] += -3 if list_full else -1
            elif op == "AGREE":
                idx = _find_rule_index(rules, text)  # type: ignore[arg-type]
                if 0 <= idx < len(rules):
                    rules[idx][1] += 1
            elif op == "EDIT":
                idx = _find_rule_index(rules, text)  # type: ignore[arg-type]
                if 0 <= idx < len(rules):
                    rules[idx][0] = text
                    rules[idx][1] += 1
            elif op == "ADD":
                rules.append([text, 2])

    # Drop rules with counter <= 0; sort descending by counter; cap at max_num_rules
    rules = [r for r in rules if r[1] > 0]
    rules.sort(key=lambda r: r[1], reverse=True)
    return [(r[0], r[1]) for r in rules[:max_num_rules]]


def format_rules(rules: List[Tuple[str, int]]) -> str:
    """Format rule list as a numbered string for prompt injection."""
    if not rules:
        return "(no rules yet)"
    return "\n".join(f"{i}. {text}" for i, (text, _) in enumerate(rules, 1))
