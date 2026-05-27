from __future__ import annotations

import copy
import json
import random
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, List

from evo_memory.core import EvoMemoryCore
from evo_memory.updater import EvoMemoryUpdater
from skill_learning.agent import format_agent_actions, serialize_message
from skill_learning.memory_cycle import FHIRBatchMemoryCycleRunner


def _inject_evo_memory(agent: Any, memory_core: EvoMemoryCore, query: str) -> Any:
    memory_block = memory_core.build_context(query)
    if not memory_block:
        return agent
    system_msg = copy.deepcopy(getattr(agent, "system_msg", []))
    if system_msg and isinstance(system_msg[0], dict):
        system_msg[0]["content"] = (
            str(system_msg[0].get("content", "")).rstrip()
            + "\n\n---\n"
            + memory_block
        )
        agent.system_msg = system_msg
    return agent


class FHIREvoMemoryCycleRunner(FHIRBatchMemoryCycleRunner):
    def __init__(self, config: Dict, run_dir: Path) -> None:
        super().__init__(config=config, run_dir=run_dir)
        self.evo_memory_dir = self.run_dir / "evo_memory"
        self.memory_core = EvoMemoryCore(self.evo_memory_dir, config.get("evo_memory", {}))
        self.memory_updater = EvoMemoryUpdater(self.updater_agent, self.memory_core)
        self._best_memory_dir = self.run_dir / "evo_memory_best"

    def _run_inner(self) -> None:
        super()._run_inner()
        print(
            f"[FHIREvoMemoryCycle] Final memory: {len(self.memory_core.semantic)} semantic rule(s), "
            f"{len(self.memory_core.episodic)} episodic record(s)"
        )

    def _maybe_update_best_checkpoint(self, val_score: float, label: Any) -> None:
        if val_score > self._best_val_score:
            self._best_val_score = val_score
            self._best_checkpoint_label = label
            if self._best_memory_dir.exists():
                shutil.rmtree(self._best_memory_dir)
            self.memory_core.snapshot_to(self._best_memory_dir)
            print(
                f"[BestCheckpoint] New best: epoch={label}, val={val_score:.1%} — "
                "Evo memory snapshot saved"
            )

    def _run_epoch(self, epoch: int, epoch_dir: Path) -> List[Dict]:
        rng = random.Random(epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)
        print(f"[Epoch {epoch}] {len(dev)} dev samples — sequential Evo memory update per episode")

        all_entries: List[Dict] = []
        updates: List[Dict] = []
        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        updates_path = epoch_dir / "evo_memory_updates.json"
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
            if updates_path.exists():
                try:
                    updates = json.loads(updates_path.read_text(encoding="utf-8"))
                except Exception:
                    updates = []
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
            semantic_before = len(self.memory_core.semantic)
            episodic_before = len(self.memory_core.episodic)
            try:
                entry = self._run_one(sample, update_cycle=sample_idx)
            except BaseException as exc:
                print(f"[FHIREvoMemoryCycle] sample failed for {sample.get('question_id')}: {exc}")
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
            entry["evo_memory_before"] = {
                "semantic": semantic_before,
                "episodic": episodic_before,
            }
            all_entries.append(entry)
            with dev_runs_path.open("a", encoding="utf-8") as f:
                safe = {k: v for k, v in entry.items() if not k.startswith("_")}
                f.write(json.dumps(safe, default=str) + "\n")

            if not entry.get("error"):
                event = self.memory_updater.update_after_episode(entry)
                event.update({
                    "epoch": epoch,
                    "sample_idx": sample_idx,
                    "semantic_before": semantic_before,
                    "episodic_before": episodic_before,
                })
                updates.append(event)
                updates_path.write_text(
                    json.dumps(updates, indent=2, default=str),
                    encoding="utf-8",
                )

        n_correct = sum(bool(e.get("is_correct")) for e in all_entries)
        print(f"[Epoch {epoch}] Dev score: {n_correct}/{len(all_entries)} | Evo updates: {len(updates)}")
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
        agent = _inject_evo_memory(agent, self.memory_core, sample["question_with_context"])
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
