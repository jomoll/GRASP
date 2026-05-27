from __future__ import annotations

import json
import random
import shutil
from pathlib import Path
from typing import Any, Dict, List

from src.memory.cycle import BatchMemoryCycleRunner
from src.skillx.agent import SkillXAwareAgent
from src.skillx.lm_adapter import SkillXLLMAdapter
from src.skillx.pipeline_adapter import SkillXPipelineAdapter
from src.skills.cycle import _make_log_entry, _serialisable


class SkillXCycleRunner(BatchMemoryCycleRunner):
    """SkillX extraction-based skill comparator.

    Reuses the benchmark/eval plumbing from BatchMemoryCycleRunner, but replaces
    the GRPO skill-editing loop with SkillX's extract-filter-merge pipeline run
    once per epoch on successful traces.
    """

    def __init__(self, config: Dict, run_dir: Path) -> None:
        super().__init__(config=config, run_dir=run_dir)

        from src.typings.general import InstanceFactory

        library_path = self.run_dir / "skillx_library.json"
        skillx_cfg = config.get("skillx", {})
        top_k = skillx_cfg.get("retrieval_top_k", 5)

        base_agent = InstanceFactory(**config["agent"]).create()
        self.memory_aware_agent = SkillXAwareAgent(base_agent, library_path, top_k=top_k)

        updater_cfg = config.get("updater", {})
        updater_agent = InstanceFactory(**updater_cfg).create() if updater_cfg else base_agent
        lm_adapter = SkillXLLMAdapter(updater_agent)

        self.skillx_adapter = SkillXPipelineAdapter(
            lm_adapter=lm_adapter,
            library_path=library_path,
            config=skillx_cfg,
        )
        self.seed: int = config.get("cycle", {}).get("seed", 0)
        self._best_library_path: Path | None = None

    def _run_inner(self) -> None:
        super()._run_inner()
        n = len(self.skillx_adapter.get_skills())
        print(f"[SkillXCycle] Final library: {n} functional skill(s)")

    def _maybe_update_best_checkpoint(self, val_score: float, label: Any) -> None:
        if val_score > self._best_val_score:
            self._best_val_score = val_score
            self._best_checkpoint_label = label
            best_dir = self.run_dir / "skillx_library_best.json"
            library_path = self.run_dir / "skillx_library.json"
            if library_path.exists():
                import shutil as _shutil
                _shutil.copy2(library_path, best_dir)
            print(
                f"[BestCheckpoint] New best: epoch={label}, val={val_score:.1%} — "
                "SkillX library snapshot saved"
            )

    def _make_best_agent(self):
        best_library = self.run_dir / "skillx_library_best.json"
        if not best_library.exists():
            return None
        from src.typings.general import InstanceFactory
        base_agent = InstanceFactory(**self.config["agent"]).create()
        top_k = self.config.get("skillx", {}).get("retrieval_top_k", 5)
        return SkillXAwareAgent(base_agent, best_library, top_k=top_k)

    def _run_epoch(self, epoch: int) -> float:
        epoch_dir = self.run_dir / f"epoch_{epoch}"
        epoch_dir.mkdir(parents=True, exist_ok=True)

        dev_runs_path = epoch_dir / "dev_runs.jsonl"

        rng = random.Random(self.seed * 1_000_000 + epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)

        all_entries: List[Dict] = []
        print(f"[Epoch {epoch}] {len(dev)} dev samples — SkillX extraction after epoch")
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

        stats = self.skillx_adapter.run_epoch(all_entries)
        stats["epoch"] = epoch
        with (epoch_dir / "skillx_updates.json").open("w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        epoch_correct = sum(e["is_correct"] for e in all_entries)
        dev_score = epoch_correct / len(all_entries) if all_entries else 0.0
        val_score = self._evaluate_val(epoch, epoch_dir, dev_score=dev_score)
        print(
            f"\n[Epoch {epoch}] Dev: {epoch_correct}/{len(all_entries)} ({dev_score:.1%}) | "
            f"Val: {val_score:.1%} | Skills extracted: {stats['n_extracted']}, "
            f"total: {stats['n_after_merge']}"
        )
        return val_score
