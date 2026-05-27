"""
SkillUpdater — proposes, validates, and applies learned skill edits.

ADD is blocked when the library is at capacity unless a REMOVE in the same batch
frees up a slot. The updater makes a single inference call per proposal (no
multi-agent pipeline).

The machinery here (classify → diagnose → propose → validate → apply, plus
revise) is benchmark-agnostic. Two pieces of *content* are injectable so the
core is not hardcoded to any one environment:

- ``task_family``: a short label naming the agent domain in prompts. If not
  given, it is inferred from the traces.
- ``task_guidance``: optional domain-specific guidance appended to the proposal
  prompt's rule list (e.g. SQL protocol priorities for a database benchmark).
- ``failure_label_examples``: example failure-mode labels shown to the
  classifier to calibrate granularity. Defaults to a general set.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from ..agent import AgentClient
from .repository import SkillRepository


_ALLOWED_ACTIONS = {"ADD", "MODIFY", "REMOVE"}
_READ_ONLY_BASE_SKILLS = {"skeleton"}

# Default failure-mode label examples shown to the classifier. These illustrate
# the right *granularity* (one label ⇒ one distinct mechanism ⇒ one skill); they
# are not a closed vocabulary. A task can override via ``failure_label_examples``.
_DEFAULT_VOCAB_EXAMPLES = (
    "  sql_max_on_text_column — used MAX() on a column stored as TEXT, "
    "so lexicographic ordering returned the wrong row\n"
    "  insert_without_verification — executed INSERT/UPDATE/DELETE then "
    "answered immediately without a follow-up SELECT to confirm the mutation\n"
    "  ls_etc_reflex_before_task_read — ran `ls /etc | wc -l` as first action "
    "before reading what the task actually requires\n"
    "  answer_submitted_before_query — reported a final answer before running "
    "any SQL or command to retrieve the value\n"
    "  where_clause_omitted — ran the right SQL function but dropped a "
    "required WHERE filter, returning an aggregate over the whole table\n"
    "  script_executed_instead_of_printed — ran the script with bash instead "
    "of printing it as the artifact the task asked for\n"
    "  wrong_column_in_mutation — UPDATE/INSERT targeted the wrong column name, "
    "causing the state hash to diverge from expected"
)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")
    return slug or "unnamed_skill"


def _extract_balanced_json_block(text: str, open_char: str, close_char: str) -> Optional[str]:
    start = text.find(open_char)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _extract_fenced_payload(text: str) -> Optional[str]:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text or "", re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _format_skill_summary(skill: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": skill.get("name", ""),
        "description": skill.get("description", ""),
        "tags": skill.get("tags") or [],
        "version": skill.get("version", 0),
    }


def _format_skill_with_stats(
    skill: Dict[str, Any],
    effectiveness: Optional[Dict[str, Any]],
) -> str:
    """One-line summary of a learned skill including provenance and runtime stats."""
    name = skill.get("name", "")
    desc = skill.get("description", "")
    version = skill.get("version", 1)
    prov = skill.get("provenance") or {}

    parts = [f"{name} (v{version})"]
    if desc:
        parts.append(f'"{desc}"')

    if prov:
        epoch = prov.get("epoch", "?")
        uc = prov.get("update_cycle", "?")
        ps = prov.get("probe_score", 0)
        pf = prov.get("fixes", 0)
        pr = prov.get("regressions", 0)
        parts.append(f"born=E{epoch}/UC{uc} probe={ps:+d}({pf}fix,{pr}regr)")

    eff = (effectiveness or {}).get(name)
    if eff:
        runs = eff.get("runs", 0)
        ef = eff.get("fixes", 0)
        er = eff.get("regressions", 0)
        parts.append(f"recent={ef}fix,{er}regr/{runs}runs")
    elif prov:
        parts.append("recent=no_data")

    return "  " + " | ".join(parts)


def _format_log(
    entries: List[Dict],
    prev_results: Optional[Dict[str, bool]] = None,
    diagnoses: Optional[Dict[str, str]] = None,
) -> str:
    lines: List[str] = []
    for entry in entries:
        sample_id = entry.get("sample_id", "unknown")
        status = entry.get("status", "unknown")
        is_correct = entry.get("is_correct", False)
        instruction = entry.get("instruction", "")
        query_type = entry.get("query_type", "other")
        error = entry.get("error")
        failure_tags = entry.get("failure_tags") or []
        actions = entry.get("agent_actions") or []
        history = entry.get("history") or []
        skill_names = [s.get("name", "") for s in entry.get("skill_snapshot_before", [])]

        transition = ""
        if prev_results is not None and sample_id in prev_results:
            prev = prev_results[sample_id]
            if prev and not is_correct:
                transition = " regression_from_prev_epoch=true"
            elif not prev and is_correct:
                transition = " recovery_from_prev_epoch=true"

        lines.append(
            f"[sample_id={sample_id} status={status} correct={is_correct}{transition}]"
        )
        if instruction:
            lines.append(f"Instruction: {instruction}")
        lines.append(f"Query type: {query_type}")
        if failure_tags:
            lines.append(f"Failure tags: {', '.join(failure_tags)}")
        if skill_names:
            lines.append(f"Learned skills before run: {', '.join(skill_names)}")
        if actions:
            lines.append("Agent actions:")
            for action in actions:
                lines.append(f"- {action}")
        if history:
            lines.append("Selected trace context:")
            for msg in history[-8:]:
                role = msg.get("role", "unknown")
                content = str(msg.get("content", "") or "").strip()
                if not content:
                    continue
                compact = re.sub(r"\s+", " ", content)
                if len(compact) > 400:
                    compact = compact[:400] + "..."
                lines.append(f"- {role}: {compact}")
        if error:
            lines.append(f"Error: {error}")
        if diagnoses and not is_correct:
            diag = diagnoses.get(str(sample_id))
            if diag:
                lines.append(f"Diagnosis: {diag}")
        lines.append("")
    return "\n".join(lines).strip()


def _infer_task_family(entries: List[Dict]) -> str:
    """Best-effort domain label from traces; used only when no task_family is set."""
    for entry in entries:
        instruction = str(entry.get("instruction", "") or "").lower()
        history = entry.get("history") or []
        history_text = " ".join(str(msg.get("content", "") or "") for msg in history).lower()
        if "mysql" in instruction or "mysql" in history_text or "action: operation" in history_text:
            return "DBBench SQL"
    return "agent"


def _extract_json_array(text: str) -> List[Any]:
    """Extract a JSON array from model output with balanced parsing."""
    candidates = []
    fenced = _extract_fenced_payload(text or "")
    if fenced:
        candidates.append(fenced)
    candidates.append(text or "")

    for candidate in candidates:
        block = _extract_balanced_json_block(candidate.strip(), "[", "]")
        if not block:
            continue
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            return data
    return []


def _build_prompt(
    entries: List[Dict],
    skill_repo: SkillRepository,
    max_proposals: int,
    max_learned_skills: int,
    prev_results: Optional[Dict[str, bool]] = None,
    skill_effectiveness: Optional[Dict[str, Any]] = None,
    failure_mode: Optional[str] = None,
    diagnosis: Optional[Dict[str, str]] = None,
    other_failing: Optional[List[Dict]] = None,
    task_family: Optional[str] = None,
    task_guidance: Optional[str] = None,
) -> str:
    all_skills = skill_repo.load_all()
    learned_skills = [s for s in all_skills if skill_repo.exists_in_learned(s["name"])]
    reference_skills = [s for s in all_skills if not skill_repo.exists_in_learned(s["name"])]

    skeleton = next((s for s in reference_skills if s["name"] == "skeleton"), None)
    non_skeleton_refs = [s for s in reference_skills if s["name"] != "skeleton"]

    editable_names = [s["name"] for s in learned_skills]
    if learned_skills:
        editable_lines = []
        for s in learned_skills:
            editable_lines.append(_format_skill_with_stats(s, skill_effectiveness))
            history = skill_repo.get_history(s["name"])
            if history:
                best_hist = max(
                    history,
                    key=lambda h: (h.get("provenance") or {}).get("probe_score", -999),
                )
                best_score = (best_hist.get("provenance") or {}).get("probe_score")
                current_score = (s.get("provenance") or {}).get("probe_score", 0)
                n_mods = len(history)
                if best_score is not None and best_score > current_score:
                    editable_lines.append(
                        f"    MODIFY-HISTORY WARNING: modified {n_mods} time(s); "
                        f"best version was v{best_hist.get('version', '?')} "
                        f"(probe_score={best_score:+d}) but current is "
                        f"probe_score={current_score:+d} — "
                        f"each MODIFY has made this skill worse. "
                        f"Strongly prefer REMOVE + ADD fresh replacement over further MODIFY."
                    )
                elif n_mods >= 2:
                    editable_lines.append(
                        f"    Note: modified {n_mods} time(s)."
                    )
        editable_skill_section = "\n".join(editable_lines)
    else:
        editable_skill_section = "(none yet)"
    reference_skill_section = (
        json.dumps([_format_skill_summary(s) for s in non_skeleton_refs], indent=2, ensure_ascii=False)
        if non_skeleton_refs else "(none)"
    )
    skeleton_section = skeleton["content"] if skeleton else "(not found)"
    log_section = _format_log(entries, prev_results=prev_results, diagnoses=diagnosis)
    family = task_family or _infer_task_family(entries)

    if other_failing:
        other_lines = []
        for e in other_failing:
            label = e.get("_failure_label", "unknown")
            instruction = str(e.get("instruction", "") or "")[:120].replace("\n", " ")
            other_lines.append(f"  [{label}] {instruction}")
        other_failing_section = (
            "\nOther active failures in this batch (different mechanisms — "
            "do NOT regress these):\n" + "\n".join(other_lines)
        )
    else:
        other_failing_section = ""

    slots_free = max_learned_skills - len(learned_skills)
    if slots_free == 0:
        skill_stats = (
            f"Learned skills in library: {len(learned_skills)} / {max_learned_skills} — LIBRARY FULL.\n"
            f"ADD is blocked. You MUST propose MODIFY or REMOVE (or both).\n"
            f"Skills with recent=0fix or recent=no_data are the weakest removal candidates.\n"
            f"To introduce a new skill, pair a REMOVE of the weakest existing skill with an ADD of the replacement in the same proposal array.\n"
            f"Editable learned skill names: {', '.join(editable_names)}"
        )
    elif slots_free <= 2:
        skill_stats = (
            f"Learned skills in library: {len(learned_skills)} / {max_learned_skills} — only {slots_free} slot(s) remaining.\n"
            f"Prefer REMOVE of a skill with recent=0fix,0regr (stale) + ADD of a better replacement over a plain ADD.\n"
            f"Editable learned skill names: {', '.join(editable_names) if editable_names else '(none yet)'}"
        )
    else:
        skill_stats = (
            f"Learned skills in library: {len(learned_skills)} / {max_learned_skills}\n"
            f"Editable learned skill names: {', '.join(editable_names) if editable_names else '(none yet)'}"
        )

    # When the library is full or nearly full the prompt asks for a REMOVE+ADD pair,
    # so allow 2 proposals per call in those cases regardless of the base max_proposals.
    effective_max_proposals = max(max_proposals, 2) if slots_free <= 2 else max_proposals

    extra_guidance = f"\n{task_guidance.strip()}" if task_guidance else ""

    return f"""You are helping improve an {family} agent's learned skill library.

You are the Skill Author. Read the current batch log and propose at most {effective_max_proposals}
skill edits as valid JSON.

--- SKILL CONTENT TEMPLATE ---
Every skill you write must follow this structure exactly. Each section is required.
{skeleton_section}
--- END TEMPLATE ---

Read-only reference/base skills for guidance only (never MODIFY or REMOVE these):
{reference_skill_section}

Editable learned skills:
{editable_skill_section}

{skill_stats}

--- PERFORMANCE LOG ---
{f"Dominant failure mode in this group: {failure_mode}" + chr(10) if failure_mode else ""}{log_section}{other_failing_section}

Return ONLY a JSON array of proposed edits:
[
  {{
    "action": "ADD | MODIFY | REMOVE",
    "name": "snake_case_skill_name",
    "description": "one-line description",
    "content": "markdown body for the skill",
    "tags": ["<keyword from task instructions>", "<natural-language synonym if needed>"]
  }}
]

Rules:
- Focus on the CURRENT BATCH only.
- Use ADD when the batch reveals a distinct failure mechanism not covered by any existing learned skill.
- Use MODIFY when an existing skill covers the right mechanism but has a missing trigger, wrong example, or incomplete action rule — fix the specific gap, do not rewrite the whole skill.
- Use REMOVE when an existing skill is redundant (fully covered by another), too vague to change behavior, or is causing regressions visible in the log. A REMOVE + ADD pair is the correct way to replace a weak skill with a better one.
- Never MODIFY or REMOVE read-only base skills such as "skeleton".
- `tags` must include the keywords that will appear in task instructions where this skill applies. The injector matches tag words against the task text at runtime, so tags must be words a task instruction would actually contain. Include both the technical term and common natural-language synonyms if tasks express the same operation differently. A skill with no tags is treated as general-purpose and gets lower injection priority, so only omit tags if the skill genuinely applies to every task type.
- Prefer reusable capability skills over narrow one-task recipes, but do not broaden a skill so much that it stops changing behavior.
- One skill must target exactly one failure mechanism.
- A good skill must change the agent's next action, query, parsing step, or verification behavior.
- Prefer CONSTRAINT skills over WORKFLOW EXPANSION skills. A constraint skill changes the form of one existing step (e.g. "include multiple columns in the WHERE clause instead of one", "CAST the year column to UNSIGNED before ordering"). A workflow expansion skill adds new mandatory intermediate steps (e.g. "run a SELECT before every UPDATE to pre-check the row"). Constraint skills are safe — they do not consume extra rounds and do not disrupt already-correct solutions. Workflow expansion skills cause regressions: the extra rounds cost turn budget from tasks the agent currently solves efficiently.
- If a proposal would only change wording, tone, or answer style, reject it unless the dominant failure is invalid protocol.
- Keep concrete operational detail. Do not broaden into vague generic skills or mini-tutorials.
- The `## Example Trajectory` section is required. Write one wrong and one correct trajectory of 2–3 turns each. Show the full Think → Act → Obs → Think → Act sequence. Do not use static code-pair examples — the trajectory must show the agent reasoning, acting, and receiving an observation.
- Use realistic task instructions and realistic action/observation text drawn from the failure traces. The wrong trajectory must show the exact failure mechanism this skill prevents. The correct trajectory must show the exact behaviour change the skill produces.
- Use specific commands, flags, fragments, error messages, output patterns, or observable triggers as examples when possible.
- Treat failure tags as strong hints about the dominant mechanism.
- Do not propose generic "verify more", "format better", or "be careful" skills if an existing learned skill already covers that behavior.
- Do not restate an existing skill with synonyms. If the mechanism is already covered, return [] or propose a narrow MODIFY with a clear missing trigger or action rule.
- Before proposing ADD, check whether any existing learned skill already targets the same failure mechanism (same trigger, same corrective action). If one does, MODIFY it instead of adding a duplicate.
- Do not encode benchmark-specific answers, row values, or hidden facts. Generalize the mechanism without leaking task content.
- Each proposal must be justified by at least one visible trigger in the trace.
- The `## When to Use This Skill` section must have a primary trigger that is observable from the task instruction alone, before the agent takes its first action — for example a word or phrase in the task, or a structural property of the task wording. Mid-task observations (error messages, empty results) may appear only in secondary "if you then observe…" guidance within the skill body, never as the primary trigger. A trigger that names only a task type is not acceptable on its own. Every skill must have at least one discriminating condition the model can evaluate before its first action.
- Before proposing a skill, silently ask:
  1. What exact trigger activates this skill?
  2. What exact behavior changes because of it?
  3. Why would that flip at least one failing sample in this batch?
  4. Is this already covered by an existing learned skill?
  5. Is the trigger condition unambiguous — could it fire on a task where the current behavior is already correct? Only use triggers that cannot fire on correct behavior.
  6. Is the primary trigger observable from the task instruction alone, before any action is taken?
- Skills should prefer realistic example identifiers from the trace pattern over placeholders, but must remain mechanism-level and reusable.
- Skill writing style:
  - All section headers must use `##` markdown (h2). Never use bold text like `**Section Name**` as a header.
  - Write from the agent's first-person perspective: "You must", "Before answering", "If you see X, do Y". Never describe a post-processing hook, monitoring system, or interceptor — the agent has no external middleware.
  - The `description` field in the JSON output must be a single line under 120 characters. All skill content belongs in `content`.
  - Never include a version number in the skill body heading or title; version tracking is handled by the frontmatter.
- NEVER propose a metacognitive or behavioral-monitoring skill. A metacognitive skill is any skill whose primary instruction is to "verify before finishing", "check whether the task is complete", "avoid looping", "ensure you have done X", "stop when done", or any form of self-monitoring. The agent already knows these rules; they cannot override generative behavior through text injection and only add noise. If the observed failure is looping, over-analysis, premature termination, or repetitive output, return [] rather than proposing a behavioral skill. Valid skills must prescribe a SPECIFIC COMMAND, QUERY PATTERN, PARSING STEP, or ENVIRONMENT-SPECIFIC MECHANIC that is demonstrably absent from the failing trace.{extra_guidance}
- If there is not enough evidence for a good edit, return [].
""".strip()


class SkillUpdater:
    def __init__(
        self,
        agent: AgentClient,
        max_proposals: int = 5,
        max_learned_skills: int = 20,
        task_family: Optional[str] = None,
        task_guidance: Optional[str] = None,
        failure_label_examples: Optional[str] = None,
    ) -> None:
        self.agent = agent
        self.max_proposals = max_proposals
        self.max_learned_skills = max_learned_skills
        self.task_family = task_family
        self.task_guidance = task_guidance
        self.failure_label_examples = failure_label_examples or _DEFAULT_VOCAB_EXAMPLES

    def classify_failures(
        self,
        entries: List[Dict],
        prev_taxonomy: Optional[Dict[str, str]] = None,
    ) -> tuple:
        """
        Classify each failing entry with a short mechanistic failure mode label.

        When prev_taxonomy is provided (label -> description from the previous epoch),
        the classifier reuses those labels when they fit and introduces new ones only
        for genuinely novel failure patterns.

        Returns (sample_to_label, new_labels) where:
          sample_to_label: {sample_id: label}
          new_labels:      {label: description} for labels not in prev_taxonomy
        Falls back to ({}, {}) on any error.
        """
        failing = [e for e in entries if not e.get("is_correct", False)]
        if not failing:
            return {}, {}

        vocab_examples = self.failure_label_examples

        if prev_taxonomy:
            taxonomy_section = (
                "Examples of well-scoped labels (these show the right specificity — "
                "generate your own specific labels, do not limit yourself to these):\n"
                + vocab_examples + "\n\n"
                "Labels used in previous epochs (reuse when the mechanism genuinely "
                "recurs; mint a new specific label when the mechanism is distinct):\n"
                + "\n".join(f'  "{k}": {v}' for k, v in prev_taxonomy.items())
            )
        else:
            taxonomy_section = (
                "Examples of well-scoped labels (these show the right specificity — "
                "generate your own specific labels, do not limit yourself to these):\n"
                + vocab_examples
            )

        def _build_lines(truncate: bool) -> list:
            result = []
            for e in failing:
                sid = e.get("sample_id", "?")
                instruction = str(e.get("instruction", "") or "")[:150].replace("\n", " ")
                tags = e.get("failure_tags") or []
                actions = e.get("agent_actions") or []
                if truncate:
                    trace_str = " → ".join(str(a)[:160].replace("\n", " ") for a in actions)
                else:
                    trace_str = " → ".join(str(a).replace("\n", " ") for a in actions)
                # Include evaluation outcome so the classifier can see WHY the task
                # failed even when the action trace looks procedurally correct.
                task_result = e.get("task_result") or {}
                reported = str(task_result.get("reported_answer", "")).replace("\n", " ")
                ground_truth = str(e.get("ground_truth", "")).replace("\n", " ")
                answer_source = task_result.get("answer_source", "")
                eval_error = str(task_result.get("error", "") or "").replace("\n", " ")
                if answer_source == "db_state_hash":
                    eval_str = f'eval=db_state_hash_mismatch reported="{reported}"'
                else:
                    eval_str = f'reported="{reported}" expected="{ground_truth}"'
                if eval_error:
                    eval_str += f' error="{eval_error}"'
                result.append(
                    f'  "{sid}": instruction="{instruction}" tags={tags} {eval_str} trace="{trace_str}"'
                )
            return result

        def _make_prompt(lines: list) -> str:
            return (
                "Classify each failing agent trace with a short mechanistic failure-mode "
                "label (3-6 words, snake_case). Each label must be specific enough that a "
                "different label implies a different skill. Classify by the exact mechanism "
                "visible in the trace — the wrong reasoning step, the wrong action, the "
                "wrong assumption — not by the domain or the surface error message.\n\n"
                "IMPORTANT: Every entry below was marked is_correct=False by the evaluator. "
                "Each one failed. If the action trace looks procedurally correct, the failure "
                "is in the final answer value (wrong row, wrong aggregation, format mismatch, "
                "or mutation that produced the wrong state). Use the reported= and expected= "
                "fields to identify the specific mismatch. Never assign the label "
                "'correct_behavior_no_failure' — if you cannot identify the mechanism from "
                "the actions, infer it from the answer/expected divergence.\n\n"
                + taxonomy_section + "\n\n"
                "Failing traces (instruction + tags + eval outcome + full action trace):\n"
                + "\n".join(lines) + "\n\n"
                "Return ONLY a JSON object with two keys:\n"
                '{\n'
                '  "labels": {"sample_id": "label", ...},\n'
                '  "new_labels": {"label": "one-line description"}\n'
                '}\n'
                '"new_labels" should contain every label that does not appear in the '
                "examples or prior-epoch labels above, with a one-line mechanism "
                'description. Set "new_labels" to {} only if every label is an exact '
                "reuse of a prior label."
            )

        def _run_attempt(lines: list) -> tuple:
            prompt = _make_prompt(lines)
            approx_chars = len(prompt)
            print(
                f"[SkillUpdater] classify_failures: ~{approx_chars:,} chars "
                f"(~{approx_chars // 4:,} est. tokens) for {len(failing)} traces"
            )
            response = self.agent.inference([{"role": "user", "content": prompt}])
            fenced = _extract_fenced_payload(response)
            raw = fenced or response
            block = _extract_balanced_json_block(raw.strip(), "{", "}")
            if not block:
                raise ValueError("no JSON block found in classifier response")
            data = json.loads(block)
            if not isinstance(data, dict):
                raise ValueError(f"classifier returned unexpected type: {type(data)}")
            sample_to_label = {
                str(k): str(v) for k, v in data.get("labels", {}).items()
                if isinstance(v, str)
            }
            # Compute new labels from the diff — don't trust LLM self-reporting.
            # Any label used in sample_to_label that isn't in prev_taxonomy is new.
            llm_descriptions = {
                str(k): str(v) for k, v in data.get("new_labels", {}).items()
                if isinstance(v, str)
            }
            known = set(prev_taxonomy or {})
            new_labels = {
                lbl: llm_descriptions.get(lbl, lbl.replace("_", " "))
                for lbl in set(sample_to_label.values())
                if lbl not in known
            }
            unique_labels = set(sample_to_label.values())
            n_reused = len(unique_labels - set(new_labels))
            print(
                f"[SkillUpdater] classified {len(failing)} failing traces → "
                f"{len(unique_labels)} mode(s) "
                f"({n_reused} reused, {len(new_labels)} new): "
                + ", ".join(
                    f"{lbl}({sum(1 for v in sample_to_label.values() if v == lbl)})"
                    for lbl in sorted(unique_labels)
                )
            )
            return sample_to_label, new_labels

        try:
            return _run_attempt(_build_lines(truncate=False))
        except Exception as e:
            print(
                f"[SkillUpdater] classify_failures failed ({e}), "
                "retrying with 160-char per-action truncation"
            )

        try:
            return _run_attempt(_build_lines(truncate=True))
        except Exception as e:
            print(f"[SkillUpdater] classify_failures retry also failed: {e}")
        return {}, {}

    def diagnose(
        self,
        entries: List[Dict],
        skill_repo: SkillRepository,
        failure_labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        For each failing entry produce a one-sentence targeted diagnosis:
        which existing skill gap or missing instruction caused the failure.
        Returns {sample_id: diagnosis_str}. Falls back to {} on any error.
        """
        failing = [e for e in entries if not e.get("is_correct", False)]
        if not failing:
            return {}

        all_skills = skill_repo.load_all()
        learned = [s for s in all_skills if skill_repo.exists_in_learned(s["name"])]
        skill_summary = (
            "\n".join(f"  [{s['name']}]: {s['description']}" for s in learned)
            if learned else "(no learned skills yet)"
        )

        lines = []
        for e in failing:
            sid = e.get("sample_id", "?")
            label = (failure_labels or {}).get(str(sid), "unknown")
            instruction = str(e.get("instruction", "") or "")[:120].replace("\n", " ")
            actions = e.get("agent_actions") or []
            trace_str = " | ".join(str(a).replace("\n", " ") for a in actions)
            lines.append(
                f'  "{sid}": label="{label}" task="{instruction}" actions="{trace_str}"'
            )

        prompt = (
            "You are diagnosing why an AI agent failed on benchmark tasks.\n\n"
            "Current learned skills:\n" + skill_summary + "\n\n"
            "Failing traces:\n" + "\n".join(lines) + "\n\n"
            "For each sample write ONE sentence identifying:\n"
            "- which existing skill should have prevented this failure but didn't "
            "(name the skill and the exact missing trigger or rule), OR\n"
            "- what new skill mechanism is needed if no existing skill is relevant.\n"
            "Be specific: name exact commands, output patterns, or decision points.\n\n"
            'Return ONLY a JSON object: {"sample_id": "one-sentence diagnosis", ...}'
        )

        try:
            response = self.agent.inference([{"role": "user", "content": prompt}])
            fenced = _extract_fenced_payload(response)
            raw = fenced or response
            block = _extract_balanced_json_block((raw or "").strip(), "{", "}")
            if block:
                data = json.loads(block)
                if isinstance(data, dict):
                    result = {str(k): str(v) for k, v in data.items() if isinstance(v, str)}
                    print(f"[SkillUpdater] diagnosed {len(result)}/{len(failing)} failing traces")
                    return result
        except Exception as e:
            print(f"[SkillUpdater] diagnose failed: {e}")
        return {}

    def revise(
        self,
        proposal: Dict,
        regression_entries: List[Dict],
        skill_repo: SkillRepository,
    ) -> List[Dict]:
        """
        Given a proposal that caused regressions, generate a revised version
        that preserves the original fixes while avoiding the regressions.
        Returns raw (unvalidated) proposals. Falls back to [] on any error.
        """
        if not regression_entries:
            return []

        regression_log = _format_log(regression_entries)
        action = proposal.get("action", "")
        name = proposal.get("name", "")
        content = proposal.get("content", "")
        description = proposal.get("description", "")

        prompt = (
            f"Your previous skill proposal caused {len(regression_entries)} regression(s) — "
            f"samples that were passing before but now fail.\n\n"
            f"Original proposal:\n"
            f"  Action: {action}\n"
            f"  Name: {name}\n"
            f"  Description: {description}\n"
            f"  Content:\n{content}\n\n"
            f"Traces of samples that REGRESSED (were passing, now failing):\n"
            f"{regression_log}\n\n"
            f"Revise the proposal so it still fixes the original failures "
            f"but no longer breaks these samples.\n"
            f"Typical fixes: narrow the trigger condition, add a guard clause that "
            f"exempts the regression pattern, or split into two more specific rules.\n"
            f"Do NOT broaden the skill or remove its core mechanism.\n\n"
            f"Return ONLY a JSON array with the revised proposal:\n"
            f'[{{"action": "{action}", "name": "{name}", '
            f'"description": "...", "content": "...", "tags": ["<keep or update to match narrowed trigger>"]}}]'
        )

        try:
            response = self.agent.inference([{"role": "user", "content": prompt}])
            proposals = _extract_json_array(response)
            return [p for p in proposals if isinstance(p, dict)]
        except Exception as e:
            print(f"[SkillUpdater] revise failed: {e}")
        return []

    def propose(
        self,
        entries: List[Dict],
        skill_repo: SkillRepository,
        prev_results: Optional[Dict[str, bool]] = None,
        skill_effectiveness: Optional[Dict[str, Any]] = None,
        failure_mode: Optional[str] = None,
        diagnosis: Optional[Dict[str, str]] = None,
        other_failing: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """Call the LLM and return raw (unvalidated) proposals."""
        prompt = _build_prompt(
            entries,
            skill_repo,
            self.max_proposals,
            self.max_learned_skills,
            prev_results=prev_results,
            skill_effectiveness=skill_effectiveness,
            failure_mode=failure_mode,
            diagnosis=diagnosis,
            other_failing=other_failing,
            task_family=self.task_family,
            task_guidance=self.task_guidance,
        )
        history = [{"role": "user", "content": prompt}]
        try:
            response = self.agent.inference(history)
            proposals = _extract_json_array(response)
            if not isinstance(proposals, list):
                print(f"[SkillUpdater] unexpected response type: {type(proposals)}")
                return []
            return [p for p in proposals if isinstance(p, dict)]
        except Exception as e:
            print(f"[SkillUpdater] inference failed: {e}")
            return []

    def validate(self, proposals: List[Dict], skill_repo: SkillRepository) -> List[Dict]:
        """Validate and normalize raw proposals before any evaluation/apply step."""
        valid: List[Dict] = []
        learned_names = {s["name"] for s in skill_repo.snapshot()}
        pending_remove_names = {
            _slugify(str(p.get("name", "")))
            for p in proposals
            if isinstance(p, dict) and str(p.get("action", "")).upper().strip() == "REMOVE"
        }

        add_slots_available = (
            self.max_learned_skills - skill_repo.learned_count() + len(pending_remove_names)
        )
        adds_reserved = 0

        for proposal in proposals:
            if not isinstance(proposal, dict):
                continue

            action = str(proposal.get("action", "")).upper().strip()
            if action not in _ALLOWED_ACTIONS:
                continue

            name = _slugify(str(proposal.get("name", "") or ""))
            description = str(proposal.get("description", "") or "").strip()
            content = str(proposal.get("content", "") or "").strip()
            tags = proposal.get("tags") or []

            if name in _READ_ONLY_BASE_SKILLS:
                print("[SkillUpdater] attempt to modify/remove base skeleton rejected")
                continue

            normalized = {
                "action": action,
                "name": name,
                "description": description,
                "content": content,
                "tags": tags,
            }

            if action == "ADD":
                if name in learned_names:
                    print(f"[SkillUpdater] ADD for existing learned skill rejected: {name}")
                    continue
                if not content:
                    continue
                if adds_reserved >= add_slots_available:
                    print(f"[SkillUpdater] ADD blocked at capacity: {name}")
                    continue
                adds_reserved += 1
                print(f"[SkillUpdater] ADD skill: {name}")
                valid.append(normalized)
                continue

            if action == "MODIFY":
                if name not in learned_names:
                    print(f"[SkillUpdater] MODIFY for unknown learned skill rejected: {name}")
                    continue
                if not content:
                    continue
                print(f"[SkillUpdater] MODIFY skill: {name}")
                valid.append(normalized)
                continue

            if action == "REMOVE":
                if name not in learned_names:
                    print(f"[SkillUpdater] REMOVE for unknown learned skill rejected: {name}")
                    continue
                print(f"[SkillUpdater] REMOVE skill: {name}")
                valid.append(normalized)

        return valid

    def apply(self, proposals: List[Dict], skill_repo: SkillRepository) -> List[Dict]:
        applied: List[Dict] = []
        for proposal in proposals:
            action = proposal["action"]
            name = proposal["name"]
            description = proposal.get("description", "")
            content = proposal.get("content", "")
            tags = proposal.get("tags") or []
            provenance = proposal.get("_provenance")  # attached by cycle, not from LLM

            if action == "ADD":
                skill_repo.add(name, description, content, tags=tags, provenance=provenance)
            elif action == "MODIFY":
                skill_repo.modify(name, description, content, tags=tags, provenance=provenance)
            elif action == "REMOVE":
                skill_repo.delete(name)
            else:
                continue
            # Strip internal keys before logging
            applied.append({k: v for k, v in proposal.items() if not k.startswith("_")})
        return applied
