from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List

from src.memory.cycle import BatchMemoryCycleRunner
from src.expel.agent import ExPeLAwareAgent
from src.expel.lm_adapter import ExPeLLMAdapter
from src.expel.pipeline_adapter import ExPeLPipelineAdapter
from src.skills.cycle import _make_log_entry, _serialisable


class ExPeLCycleRunner(BatchMemoryCycleRunner):
    """ExpeL contrastive-rule comparator.

    Reuses BatchMemoryCycleRunner plumbing; replaces the memory update loop
    with ExpeL's compare-critique pipeline run once per epoch on all dev traces.
    """

    def __init__(self, config: Dict, run_dir: Path) -> None:
        super().__init__(config=config, run_dir=run_dir)

        from src.typings.general import InstanceFactory

        expel_cfg = config.get("expel", {})

        base_agent = InstanceFactory(**config["agent"]).create()

        updater_cfg = config.get("updater", {})
        updater_agent = InstanceFactory(**updater_cfg).create() if updater_cfg else base_agent
        lm_adapter = ExPeLLMAdapter(updater_agent)

        self.expel_adapter = ExPeLPipelineAdapter(
            lm_adapter=lm_adapter,
            rules_path=self.run_dir / "expel_rules.json",
            store_path=self.run_dir / "expel_store.json",
            config=expel_cfg,
        )
        self.memory_aware_agent = ExPeLAwareAgent(base_agent, self.expel_adapter)
        self.seed: int = config.get("cycle", {}).get("seed", 0)

    def _run_inner(self) -> None:
        super()._run_inner()
        print(f"[ExPeLCycle] Final rule count: {len(self.expel_adapter.rules)}")

    def _maybe_update_best_checkpoint(self, val_score: float, label: Any) -> None:
        if val_score > self._best_val_score:
            self._best_val_score = val_score
            self._best_checkpoint_label = label
            import shutil
            for fname in ("expel_rules.json", "expel_store.json"):
                src = self.run_dir / fname
                if src.exists():
                    shutil.copy2(src, self.run_dir / fname.replace(".json", "_best.json"))
            print(
                f"[BestCheckpoint] New best: epoch={label}, val={val_score:.1%} — "
                "ExpeL rules snapshot saved"
            )

    def _make_best_agent(self):
        rules_best = self.run_dir / "expel_rules_best.json"
        if not rules_best.exists():
            return None
        from src.typings.general import InstanceFactory
        base_agent = InstanceFactory(**self.config["agent"]).create()
        store_best = self.run_dir / "expel_store_best.json"
        lm_adapter = ExPeLLMAdapter(base_agent)
        best_adapter = ExPeLPipelineAdapter(
            lm_adapter=lm_adapter,
            rules_path=rules_best,
            store_path=store_best if store_best.exists() else self.run_dir / "expel_store.json",
            config=self.config.get("expel", {}),
        )
        return ExPeLAwareAgent(base_agent, best_adapter)

    def _run_epoch(self, epoch: int) -> float:
        epoch_dir = self.run_dir / f"epoch_{epoch}"
        epoch_dir.mkdir(parents=True, exist_ok=True)

        dev_runs_path = epoch_dir / "dev_runs.jsonl"

        rng = random.Random(self.seed * 1_000_000 + epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)

        all_entries: List[Dict] = []
        print(f"[Epoch {epoch}] {len(dev)} dev samples — ExpeL critique after epoch")
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
            result, is_correct = self._run_single(sample)
            entry = _make_log_entry(sample, result, is_correct, sample_idx, [])
            all_entries.append(entry)
            with dev_runs_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(_serialisable(entry), ensure_ascii=False) + "\n")

        stats = self.expel_adapter.run_epoch(all_entries)
        stats["epoch"] = epoch
        with (epoch_dir / "expel_updates.json").open("w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        epoch_correct = sum(e["is_correct"] for e in all_entries)
        dev_score = epoch_correct / len(all_entries) if all_entries else 0.0
        val_score = self._evaluate_val(epoch, epoch_dir, dev_score=dev_score)
        print(
            f"\n[Epoch {epoch}] Dev: {epoch_correct}/{len(all_entries)} ({dev_score:.1%}) | "
            f"Val: {val_score:.1%} | Rules: {stats['n_rules']} "
            f"(pairs critiqued: {stats['n_pairs_critiqued']})"
        )
        return val_score
