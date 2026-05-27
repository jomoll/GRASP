from __future__ import annotations

import json
import random
import shutil
from pathlib import Path
from typing import Any, Dict, List

from src.client.agents.evo_memory_aware_agent import EvoMemoryAwareAgent
from src.evo_memory.core import EvoMemoryCore
from src.evo_memory.updater import EvoMemoryUpdater
from src.memory.cycle import BatchMemoryCycleRunner
from src.skills.cycle import _make_log_entry, _serialisable


class EvoMemoryCycleRunner(BatchMemoryCycleRunner):
    """Evo-style structured memory comparator.

    Reuses the benchmark/eval plumbing from BatchMemoryCycleRunner, but replaces
    flat failure-only notes with retrieved episodic + semantic memory curated
    after every completed dev episode.
    """

    def __init__(self, config: Dict, run_dir: Path) -> None:
        super().__init__(config=config, run_dir=run_dir)

        from src.typings.general import InstanceFactory

        self.evo_memory_dir = self.run_dir / "evo_memory"
        self.memory_core = EvoMemoryCore(self.evo_memory_dir, config.get("evo_memory", {}))

        base_agent = InstanceFactory(**config["agent"]).create()
        self.memory_aware_agent = EvoMemoryAwareAgent(base_agent, self.memory_core)

        updater_cfg = config.get("updater", {})
        updater_agent = InstanceFactory(**updater_cfg).create() if updater_cfg else base_agent
        self.memory_updater = EvoMemoryUpdater(updater_agent, self.memory_core)

        self._best_memory_dir = self.run_dir / "evo_memory_best"

    def _run_inner(self) -> None:
        super()._run_inner()
        print(
            f"[EvoMemoryCycle] Final memory: {len(self.memory_core.semantic)} semantic rule(s), "
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

    def _make_best_agent(self):
        if not self._best_memory_dir.exists():
            return None
        from src.typings.general import InstanceFactory
        base_agent = InstanceFactory(**self.config["agent"]).create()
        best_core = EvoMemoryCore(self._best_memory_dir, self.config.get("evo_memory", {}))
        return EvoMemoryAwareAgent(base_agent, best_core)

    def _run_epoch(self, epoch: int) -> float:
        epoch_dir = self.run_dir / f"epoch_{epoch}"
        epoch_dir.mkdir(parents=True, exist_ok=True)

        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        updates_path = epoch_dir / "evo_memory_updates.json"

        rng = random.Random(epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)

        all_entries: List[Dict] = []
        update_events: List[Dict] = []

        print(f"[Epoch {epoch}] {len(dev)} dev samples — sequential Evo memory update per episode")
        sample_by_id = {str(sample.get("id")): sample for sample in dev}
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
                    update_events = json.loads(updates_path.read_text(encoding="utf-8"))
                except Exception:
                    update_events = []
            if completed_by_id:
                print(
                    f"[Resume] loaded {len(completed_by_id)}/{len(dev)} "
                    f"completed dev samples from {dev_runs_path}",
                    flush=True,
                )

        for sample_idx, sample in enumerate(dev):
            sample_id = str(sample.get("id"))
            if sample_id in completed_by_id:
                all_entries.append(completed_by_id[sample_id])
                continue
            semantic_before = len(self.memory_core.semantic)
            episodic_before = len(self.memory_core.episodic)

            result, is_correct = self._run_single(sample)
            entry = _make_log_entry(sample, result, is_correct, sample_idx, [])
            entry["evo_memory_before"] = {
                "semantic": semantic_before,
                "episodic": episodic_before,
            }
            all_entries.append(entry)

            with dev_runs_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(_serialisable(entry), ensure_ascii=False) + "\n")

            if not entry.get("error"):
                event = self.memory_updater.update_after_episode(entry)
                event.update({
                    "epoch": epoch,
                    "sample_idx": sample_idx,
                    "semantic_before": semantic_before,
                    "episodic_before": episodic_before,
                })
                update_events.append(event)

        with updates_path.open("w", encoding="utf-8") as f:
            json.dump(update_events, f, indent=2, ensure_ascii=False)

        epoch_correct = sum(e["is_correct"] for e in all_entries)
        epoch_total = len(all_entries)
        dev_score = epoch_correct / epoch_total if epoch_total > 0 else 0.0

        val_score = self._evaluate_val(epoch, epoch_dir, dev_score=dev_score)
        print(
            f"\n[Epoch {epoch}] Dev: {epoch_correct}/{epoch_total} ({dev_score:.1%}) | "
            f"Val: {val_score:.1%} | Evo updates: {len(update_events)}"
        )
        return val_score
