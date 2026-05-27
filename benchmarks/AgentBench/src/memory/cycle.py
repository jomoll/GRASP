"""
BatchMemoryCycleRunner / MemoryCycleRunner — memory-based comparators to the skill-learning cycle.

BatchMemoryCycleRunner: runs dev samples in parallel batches; updates memory once per batch.
MemoryCycleRunner: sequential variant matching the original MedAgentBench-v2 paper — updates
    memory immediately after each individual failing sample.

Both use MemoryAwareAgent (injects memory.json into every agent turn) and MemoryUpdater
(LLM proposes 1-3 correction bullets; condenses when at max_bullets capacity).

Output layout (inside run_dir/):
    config.yaml
    memory.json                 flat list of correction bullets
    memory/best.json            copy at the best val epoch
    epoch_0/
        dev_runs.jsonl
        memory_updates.json
        val_score.json
    val_scores.json
"""

import io
import json
import random
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

from src.client.agents.memory_aware_agent import MemoryAwareAgent
from src.client.task import TaskClient
from src.memory.updater import MemoryUpdater
from src.skills.cycle import (
    _load_eval_fn,
    _load_json_list_or_empty,
    _load_required_json_list,
    _make_log_entry,
    _score_result,
    _serialisable,
    _TeeStream,
)


class BatchMemoryCycleRunner:
    def __init__(self, config: Dict, run_dir: Path) -> None:
        self.config = config
        self.run_dir = Path(run_dir)

        cycle_cfg = config["cycle"]
        self.epochs: int = cycle_cfg["epochs"]
        self.update_every: int = cycle_cfg["update_every"]
        self.batch_concurrency: int = cycle_cfg.get("batch_concurrency", 5)
        self.run_baseline: bool = cycle_cfg.get("run_baseline", True)

        memory_cfg = config.get("memory", {})
        self.max_bullets: int = memory_cfg.get("max_bullets", 20)

        self._eval_fn = _load_eval_fn(config)

        task_cfg = config["task"]
        self.dev_data = _load_required_json_list(Path(config["data"]["dev"]), "dev split")
        self.val_data = _load_required_json_list(Path(config["data"]["val"]), "val split")
        self._id_to_index: Dict[str, str] = {s["id"]: s["id"] for s in self.dev_data + self.val_data}

        self.task_client = TaskClient(
            name=task_cfg["name"],
            controller_address=task_cfg["controller_address"],
        )

        self.memory_path = self.run_dir / "memory.json"

        from src.typings.general import InstanceFactory
        base_agent = InstanceFactory(**config["agent"]).create()
        self.memory_aware_agent = MemoryAwareAgent(base_agent, self.memory_path)

        # Updater uses same agent by default; optionally a separate one
        updater_cfg = config.get("updater", {})
        if updater_cfg:
            updater_agent = InstanceFactory(**updater_cfg).create()
        else:
            updater_agent = base_agent
        self.memory_updater = MemoryUpdater(updater_agent, max_bullets=self.max_bullets)

        self._val_scores_path = self.run_dir / "val_scores.json"
        self._best_val_score: float = 0.0
        self._best_checkpoint_label: Any = None
        self._best_memory_path: Path = self.run_dir / "memory" / "best.json"
        self._progress_stream = None
        self.resume: bool = bool(config.get("_resume", False))

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        log_path = self.run_dir / "run.log"
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)

        central_log_dir = self.run_dir.parent.parent.parent.parent / "logs"
        central_log_dir.mkdir(parents=True, exist_ok=True)
        central_log_path = central_log_dir / f"memory_cycle_{self.run_dir.parent.name}_{self.run_dir.name}.log"
        central_log_file = open(central_log_path, "a", encoding="utf-8", buffering=1)

        original_stdout = sys.stdout
        original_stderr = sys.stderr
        self._progress_stream = (
            original_stderr
            if tqdm is not None and getattr(original_stderr, "isatty", lambda: False)()
            else None
        )
        sys.stdout = _TeeStream(original_stdout, _TeeStream(log_file, central_log_file))
        sys.stderr = _TeeStream(original_stderr, _TeeStream(log_file, central_log_file))
        try:
            self._run_inner()
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            self._progress_stream = None
            log_file.close()
            central_log_file.close()

    def _progress(self, iterable, *, total=None, desc="", leave=False, position=None):
        if tqdm is None or self._progress_stream is None:
            return iterable
        kwargs = {"total": total, "desc": desc, "leave": leave,
                  "file": self._progress_stream, "dynamic_ncols": True}
        if position is not None:
            kwargs["position"] = position
        return tqdm(iterable, **kwargs)

    def _run_inner(self) -> None:
        if self.run_baseline:
            baseline_dir = self.run_dir / "baseline"
            baseline_score_path = baseline_dir / "val_score.json"
            if self.resume and baseline_score_path.exists():
                try:
                    s = json.loads(baseline_score_path.read_text(encoding="utf-8"))["score"]
                    print(f"[Resume] Baseline already done (val={s:.1%}), skipping")
                except Exception:
                    pass
            else:
                print(f"\n{'='*60}")
                print("  BASELINE (before epoch 0)")
                print(f"{'='*60}")
                baseline_dir.mkdir(exist_ok=True)
                baseline_score = self._evaluate_val(epoch="baseline", epoch_dir=baseline_dir)
                print(f"[Baseline] Val: {baseline_score:.1%}")

        for epoch in range(self.epochs):
            epoch_dir = self.run_dir / f"epoch_{epoch}"
            val_score_path = epoch_dir / "val_score.json"
            if self.resume and val_score_path.exists():
                try:
                    s = json.loads(val_score_path.read_text(encoding="utf-8"))["score"]
                    print(f"[Resume] Epoch {epoch} already done (val={s:.1%}), skipping")
                    if s > self._best_val_score:
                        self._best_val_score = s
                        self._best_checkpoint_label = epoch
                except Exception:
                    pass
                continue
            if self.resume:
                resumed = self._resume_epoch_val_if_dev_complete(epoch, epoch_dir)
                if resumed is not None:
                    val_score = resumed
                    self._maybe_update_best_checkpoint(val_score, epoch)
                    continue
            print(f"\n{'='*60}")
            print(f"  EPOCH {epoch}")
            print(f"{'='*60}")
            val_score = self._run_epoch(epoch)
            self._maybe_update_best_checkpoint(val_score, epoch)

        print("\n[MemoryCycle] Training complete.")
        self._print_learning_curve()
        final_bullets = []
        if self.memory_path.exists():
            try:
                final_bullets = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        print(f"[MemoryCycle] Final memory: {len(final_bullets)} bullet(s)")

    # ------------------------------------------------------------------
    # Epoch
    # ------------------------------------------------------------------

    def _load_dev_run_entries(self, path: Path) -> List[Dict]:
        entries: List[Dict] = []
        if not path.exists():
            return entries
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "sample_id" in entry:
                    entries.append(entry)
        return entries

    def _resume_epoch_val_if_dev_complete(
        self,
        epoch: int,
        epoch_dir: Path,
    ) -> Optional[float]:
        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        entries = self._load_dev_run_entries(dev_runs_path)
        if not entries:
            return None

        expected_ids = {str(sample["id"]) for sample in self.dev_data}
        latest_by_id: Dict[str, Dict] = {}
        for entry in entries:
            sample_id = str(entry.get("sample_id"))
            if sample_id in expected_ids:
                latest_by_id[sample_id] = entry

        missing = expected_ids - set(latest_by_id)
        if missing:
            print(
                f"[Resume] Epoch {epoch} has {len(latest_by_id)}/{len(expected_ids)} "
                "dev samples; rerunning epoch"
            )
            return None

        epoch_correct = sum(
            1 for entry in latest_by_id.values() if entry.get("is_correct") is True
        )
        epoch_total = len(expected_ids)
        dev_score = epoch_correct / epoch_total if epoch_total else 0.0

        print(f"\n{'='*60}")
        print(f"  EPOCH {epoch}")
        print(f"{'='*60}")
        print(
            f"[Resume] Epoch {epoch} dev already complete "
            f"({epoch_correct}/{epoch_total}, {dev_score:.1%}); running val only"
        )
        val_score = self._evaluate_val(epoch, epoch_dir, dev_score=dev_score)
        print(f"\n[Epoch {epoch}] Dev: {epoch_correct}/{epoch_total} "
              f"({dev_score:.1%}) | Val: {val_score:.1%}")
        return val_score

    def _load_prev_results(self, epoch: int) -> Optional[Dict[str, bool]]:
        if epoch == 0:
            return None
        prev_path = self.run_dir / f"epoch_{epoch - 1}" / "dev_runs.jsonl"
        if not prev_path.exists():
            return None
        results = {}
        with open(prev_path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    results[entry["sample_id"]] = entry["is_correct"]
                except (json.JSONDecodeError, KeyError):
                    pass
        return results

    def _run_epoch(self, epoch: int) -> float:
        epoch_dir = self.run_dir / f"epoch_{epoch}"
        epoch_dir.mkdir(parents=True, exist_ok=True)

        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        updates_path = epoch_dir / "memory_updates.json"

        rng = random.Random(epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)

        all_entries: List[Dict] = []
        update_events: List[Dict] = []
        update_cycle = 0

        batches = [dev[i: i + self.update_every] for i in range(0, len(dev), self.update_every)]
        print(f"[Epoch {epoch}] {len(dev)} dev samples — "
              f"{len(batches)} batches of ≤{self.update_every}")

        for batch_idx, batch in enumerate(batches):
            # Snapshot memory size before this batch runs
            current_bullets: List[str] = []
            if self.memory_path.exists():
                try:
                    current_bullets = json.loads(self.memory_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            memory_version_before = len(current_bullets)

            print(f"\n  Batch {batch_idx}/{len(batches)-1} "
                  f"(update_cycle={update_cycle}, {len(batch)} samples, "
                  f"memory={memory_version_before} bullets)")

            entries = self._run_batch(batch, update_cycle, memory_version_before)
            all_entries.extend(entries)

            with open(dev_runs_path, "a", encoding="utf-8") as f:
                for e in entries:
                    f.write(json.dumps(_serialisable(e), ensure_ascii=False) + "\n")

            n_correct = sum(e["is_correct"] for e in entries)
            print(f"  Batch score: {n_correct}/{len(entries)}")

            # Unconditional memory update from this batch's failures
            failing_entries = [e for e in entries if not e["is_correct"] and not e.get("error")]
            print(f"  Updating memory from {len(failing_entries)} failing trace(s)...")
            updated_bullets = self.memory_updater.update(self.memory_path, failing_entries)

            event = {
                "epoch": epoch,
                "update_cycle": update_cycle,
                "batch_size": len(batch),
                "batch_correct": n_correct,
                "n_failing": len(failing_entries),
                "new_bullets": updated_bullets[memory_version_before:],
                "memory_size": len(updated_bullets),
            }
            update_events.append(event)
            update_cycle += 1

        with open(updates_path, "w", encoding="utf-8") as f:
            json.dump(update_events, f, indent=2, ensure_ascii=False)

        epoch_correct = sum(e["is_correct"] for e in all_entries)
        epoch_total = len(all_entries)
        dev_score = epoch_correct / epoch_total if epoch_total > 0 else 0.0

        val_score = self._evaluate_val(epoch, epoch_dir, dev_score=dev_score)
        print(f"\n[Epoch {epoch}] Dev: {epoch_correct}/{epoch_total} "
              f"({dev_score:.1%}) | Val: {val_score:.1%}")
        return val_score

    # ------------------------------------------------------------------
    # Best-checkpoint management
    # ------------------------------------------------------------------

    def _maybe_update_best_checkpoint(self, val_score: float, label: Any) -> None:
        if val_score > self._best_val_score:
            self._best_val_score = val_score
            self._best_checkpoint_label = label
            self._best_memory_path.parent.mkdir(parents=True, exist_ok=True)
            if self.memory_path.exists():
                shutil.copy2(self.memory_path, self._best_memory_path)
            print(
                f"[BestCheckpoint] New best: epoch={label}, val={val_score:.1%} — "
                "memory snapshot saved"
            )

    # ------------------------------------------------------------------
    # Batch execution (parallel)
    # ------------------------------------------------------------------

    def _run_batch(self, batch: List[Dict], update_cycle: int,
                   memory_version_before: int) -> List[Dict]:
        entries = [None] * len(batch)

        def run_one(idx: int, sample: Dict):
            return idx, self._run_single(sample)

        with ThreadPoolExecutor(max_workers=self.batch_concurrency) as pool:
            futures = {pool.submit(run_one, i, s): i for i, s in enumerate(batch)}
            for future in self._progress(
                as_completed(futures), total=len(futures),
                desc=f"Dev batch {update_cycle}", leave=False, position=1,
            ):
                idx, (result, is_correct) = future.result()
                entry = _make_log_entry(batch[idx], result, is_correct, update_cycle, [])
                entry["memory_version_before"] = memory_version_before
                entries[idx] = entry

        return entries

    def _run_single(self, sample: Dict):
        task_index = self._id_to_index[sample["id"]]
        from src.client.task import TaskError
        attempt = 0
        while True:
            result = self.task_client.run_sample(task_index, self.memory_aware_agent)
            if result.error != TaskError.NOT_AVAILABLE.value:
                break
            wait = min(5 * (attempt + 1), 30)
            print(f"[MemoryCycle] {sample['id']} not available, retry in {wait}s")
            time.sleep(wait)
            attempt += 1
        is_correct = _score_result(sample, result, self._eval_fn)
        return result, is_correct

    # ------------------------------------------------------------------
    # Val evaluation
    # ------------------------------------------------------------------

    def _evaluate_val(self, epoch, epoch_dir: Path, dev_score: float = None) -> float:
        print(f"\n  [Val] evaluating {len(self.val_data)} samples...")
        correct = 0
        total = len(self.val_data)
        val_entries = [None] * total

        def run_one(idx: int, sample: Dict):
            task_index = self._id_to_index[sample["id"]]
            from src.client.task import TaskError
            for attempt in range(3):
                result = self.task_client.run_sample(task_index, self.memory_aware_agent)
                if result.error != TaskError.NOT_AVAILABLE.value:
                    break
                time.sleep(5 * (attempt + 1))
            is_correct = _score_result(sample, result, self._eval_fn)
            status = result.output.status if result.output else result.error
            task_result = result.output.result if result.output else None
            error_info = result.info if result.output is None else None
            return idx, is_correct, status, task_result, error_info

        with ThreadPoolExecutor(max_workers=self.batch_concurrency) as pool:
            futures = {pool.submit(run_one, i, s): i for i, s in enumerate(self.val_data)}
            for future in self._progress(
                as_completed(futures), total=len(futures),
                desc=f"Val {epoch}", leave=False, position=1,
            ):
                idx, is_correct, status, task_result, error_info = future.result()
                val_entries[idx] = {
                    "sample_id": self.val_data[idx]["id"],
                    "is_correct": is_correct,
                    "status": status,
                    "result": task_result,
                    "error_info": error_info,
                }
                if is_correct:
                    correct += 1

        score = correct / total if total > 0 else 0.0

        with open(epoch_dir / "val_runs.jsonl", "w") as f:
            for entry in val_entries:
                f.write(json.dumps(entry) + "\n")

        val_score_record = {"epoch": epoch, "score": score,
                            "n_correct": correct, "n_total": total, "dev_score": dev_score}
        with open(epoch_dir / "val_score.json", "w") as f:
            json.dump(val_score_record, f, indent=2)

        curve = _load_json_list_or_empty(self._val_scores_path, "val learning curve")
        curve.append(val_score_record)
        with open(self._val_scores_path, "w") as f:
            json.dump(curve, f, indent=2)

        return score

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _print_learning_curve(self) -> None:
        if not self._val_scores_path.exists():
            return
        curve = _load_json_list_or_empty(self._val_scores_path, "val learning curve")
        if not curve:
            return
        print("\nVal learning curve:")
        for entry in curve:
            bar = "█" * int(entry["score"] * 20)
            label = f"{entry['epoch']:>8}" if isinstance(entry["epoch"], int) else f"{'baseline':>8}"
            print(f"  {label}: {entry['score']:.1%}  {bar}")


class MemoryCycleRunner(BatchMemoryCycleRunner):
    """Sequential variant matching the original MedAgentBench-v2 paper.

    Memory is updated immediately after each individual failing sample rather than
    after a full batch. Dev samples are run one at a time (no parallelism); val
    evaluation is still parallelised via the inherited _evaluate_val.
    """

    def _run_epoch(self, epoch: int) -> float:
        epoch_dir = self.run_dir / f"epoch_{epoch}"
        epoch_dir.mkdir(parents=True, exist_ok=True)

        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        updates_path = epoch_dir / "memory_updates.json"

        rng = random.Random(epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)

        all_entries: List[Dict] = []
        update_events: List[Dict] = []
        n_updates = 0

        print(f"[Epoch {epoch}] {len(dev)} dev samples — sequential, update per failure")

        for sample_idx, sample in enumerate(dev):
            current_bullets: List[str] = []
            if self.memory_path.exists():
                try:
                    current_bullets = json.loads(self.memory_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            memory_version_before = len(current_bullets)

            result, is_correct = self._run_single(sample)
            entry = _make_log_entry(sample, result, is_correct, n_updates, [])
            entry["memory_version_before"] = memory_version_before
            all_entries.append(entry)

            with open(dev_runs_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(_serialisable(entry), ensure_ascii=False) + "\n")

            if not is_correct and not entry.get("error"):
                updated_bullets = self.memory_updater.update(self.memory_path, [entry])
                update_events.append({
                    "epoch": epoch,
                    "sample_idx": sample_idx,
                    "sample_id": sample["id"],
                    "memory_version_before": memory_version_before,
                    "new_bullets": updated_bullets[memory_version_before:],
                    "memory_size": len(updated_bullets),
                })
                n_updates += 1

        with open(updates_path, "w", encoding="utf-8") as f:
            json.dump(update_events, f, indent=2, ensure_ascii=False)

        epoch_correct = sum(e["is_correct"] for e in all_entries)
        epoch_total = len(all_entries)
        dev_score = epoch_correct / epoch_total if epoch_total > 0 else 0.0

        val_score = self._evaluate_val(epoch, epoch_dir, dev_score=dev_score)
        print(f"\n[Epoch {epoch}] Dev: {epoch_correct}/{epoch_total} "
              f"({dev_score:.1%}) | Val: {val_score:.1%} | Updates: {n_updates}")
        return val_score
