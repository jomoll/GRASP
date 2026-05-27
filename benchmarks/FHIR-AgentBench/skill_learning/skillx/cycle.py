from __future__ import annotations

import json
import random
import traceback
from pathlib import Path
from typing import Any, Dict, List

from skill_learning.agent import LiteLLMAgent, format_agent_actions, serialize_message
from skill_learning.memory_cycle import FHIRBatchMemoryCycleRunner
from skill_learning.skillx.lm_adapter import SkillXLLMAdapter
from skill_learning.skillx.pipeline_adapter import SkillXPipelineAdapter


def _inject_skillx(agent: Any, skill_block: str) -> Any:
    """Prepend skill block to the agent's system message."""
    import copy
    if not skill_block:
        return agent
    system_msg = copy.deepcopy(getattr(agent, "system_msg", []))
    if system_msg and isinstance(system_msg[0], dict):
        system_msg[0]["content"] = (
            str(system_msg[0].get("content", "")).rstrip()
            + "\n\n---\n"
            + skill_block
        )
        agent.system_msg = system_msg
    return agent


class FHIRSkillXCycleRunner(FHIRBatchMemoryCycleRunner):
    """SkillX extraction-based skill comparator for FHIR-AgentBench.

    Runs SkillX extraction on successful dev traces at the end of each epoch.
    Injects retrieved skills into the system prompt at inference.
    """

    def __init__(self, config: Dict, run_dir: Path) -> None:
        super().__init__(config=config, run_dir=run_dir)

        library_path = self.run_dir / "skillx_library.json"
        skillx_cfg = config.get("skillx", {})
        self.skillx_top_k: int = skillx_cfg.get("retrieval_top_k", 5)

        updater_cfg = config.get("updater", {})
        updater_agent = LiteLLMAgent(
            model=updater_cfg.get("model", self.agent_model),
            base_url=updater_cfg.get("base_url", self.agent_base_url),
            temperature=float(updater_cfg.get("temperature", 0.7)),
        )
        lm_adapter = SkillXLLMAdapter(updater_agent)

        self.skillx_adapter = SkillXPipelineAdapter(
            lm_adapter=lm_adapter,
            library_path=library_path,
            config=skillx_cfg,
        )

    def _run_inner(self) -> None:
        super()._run_inner()
        n = len(self.skillx_adapter.get_skills())
        print(f"[FHIRSkillXCycle] Final library: {n} functional skill(s)")

    def _maybe_update_best_checkpoint(self, val_score: float, label: Any) -> None:
        if val_score > self._best_val_score:
            self._best_val_score = val_score
            self._best_checkpoint_label = label
            library_path = self.run_dir / "skillx_library.json"
            best_path = self.run_dir / "skillx_library_best.json"
            if library_path.exists():
                import shutil
                shutil.copy2(library_path, best_path)
            print(
                f"[BestCheckpoint] New best: epoch={label}, val={val_score:.1%} — "
                "SkillX library snapshot saved"
            )

    def _run_epoch(self, epoch: int, epoch_dir: Path) -> List[Dict]:
        rng = random.Random(epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)
        print(f"[Epoch {epoch}] {len(dev)} dev samples — SkillX extraction after epoch")

        all_entries: List[Dict] = []
        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        sample_by_id = {str(sample.get("question_id")): sample for sample in dev}
        completed_by_id: Dict[str, Dict] = {}

        if self.resume and dev_runs_path.exists():
            with dev_runs_path.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    sid = str(entry.get("sample_id"))
                    if sid not in sample_by_id or sid in completed_by_id:
                        continue
                    completed_by_id[sid] = entry
            if completed_by_id:
                print(
                    f"[Resume] loaded {len(completed_by_id)}/{len(dev)} "
                    f"completed dev samples from {dev_runs_path}",
                    flush=True,
                )
        else:
            dev_runs_path.touch(exist_ok=True)

        for sample_idx, sample in enumerate(dev):
            sample_id = str(sample.get("question_id"))
            if sample_id in completed_by_id:
                all_entries.append(completed_by_id[sample_id])
                continue
            try:
                entry = self._run_one(sample, update_cycle=sample_idx)
            except BaseException as exc:
                entry = {
                    "sample_id": sample.get("question_id"),
                    "instruction": sample.get("question"),
                    "query_type": sample.get("template") or sample.get("main_table_name"),
                    "is_correct": False,
                    "update_cycle": sample_idx,
                    "status": "runner_error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "ground_truth": sample.get("true_answer"),
                    "task_result": {},
                    "agent_actions": [],
                    "history": [],
                    "failure_tags": [
                        str(x) for x in [sample.get("template"), sample.get("main_table_name")] if x
                    ],
                }
            all_entries.append(entry)
            with dev_runs_path.open("a", encoding="utf-8") as f:
                safe = {k: v for k, v in entry.items() if not k.startswith("_")}
                f.write(json.dumps(safe, default=str) + "\n")

        stats = self.skillx_adapter.run_epoch(all_entries)
        stats["epoch"] = epoch
        with (epoch_dir / "skillx_updates.json").open("w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        n_correct = sum(bool(e.get("is_correct")) for e in all_entries)
        print(
            f"[Epoch {epoch}] Dev score: {n_correct}/{len(all_entries)} | "
            f"Skills extracted: {stats['n_extracted']}, total: {stats['n_after_merge']}"
        )
        return all_entries

    def _run_one(self, sample: Dict, update_cycle: int) -> Dict:
        import tools.cache as cache_module
        from core_utils import create_agent, parse_outputs

        cache_module.CACHE_ENABLED = bool(self.config.get("agent", {}).get("enable_cache", True))

        agent = create_agent(
            self.agent_strategy,
            self.agent_model,
            verbose=self.verbose_agent,
            base_url=self.agent_base_url,
            timeout=self.agent_timeout,
            max_retries=self.agent_max_retries,
        )
        skill_block = self.skillx_adapter.build_skill_block(
            sample["question_with_context"], top_k=self.skillx_top_k
        )
        agent = _inject_skillx(agent, skill_block)

        try:
            raw_output = agent.run(sample["question_with_context"])
            parsed = parse_outputs(raw_output)
        except Exception as exc:
            raw_output = {"error": str(exc), "trace": []}
            parsed = {
                "agent_answer": None,
                "agent_fhir_resources": None,
                "trace": [],
                "usage": None,
                "error": str(exc),
            }

        trace = [
            serialize_message(m)
            for m in (parsed.get("trace") or raw_output.get("trace") or [])
            if m is not None
        ]
        is_correct = self.evaluator.score(sample, parsed)
        return {
            "sample_id": sample["question_id"],
            "instruction": sample["question"],
            "context": sample.get("question_with_context"),
            "query_type": sample.get("template") or sample.get("main_table_name"),
            "is_correct": is_correct,
            "update_cycle": update_cycle,
            "status": "completed" if not parsed.get("error") else "agent_error",
            "error": parsed.get("error"),
            "ground_truth": sample.get("true_answer"),
            "task_result": {
                "reported_answer": parsed.get("agent_answer"),
                "retrieved_fhir_resources": parsed.get("agent_fhir_resources"),
                "usage": parsed.get("usage"),
            },
            "agent_actions": format_agent_actions(trace),
            "history": trace,
            "failure_tags": [
                str(x) for x in [sample.get("template"), sample.get("main_table_name")] if x
            ],
            "_sample": sample,
        }
