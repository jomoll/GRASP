"""
BatchMemoryCycleRunner / MemoryCycleRunner — memory-based comparators to the MedAgentBench
skill-learning cycle.

BatchMemoryCycleRunner: runs dev samples in parallel batches; updates memory once per batch.
MemoryCycleRunner: sequential variant matching the original MedAgentBench-v2 paper — updates
    memory immediately after each individual failing sample.

MedAgentBench-specific: _score_result takes fhir_api_base (not eval_fn); no _load_eval_fn.
"""

import json
import random
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

from src.client.agents.memory_aware_agent import MemoryAwareAgent
from src.client.task import TaskClient
from src.memory.updater import MemoryUpdater
from src.skills.cycle import (
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

        task_cfg = config["task"]
        self.fhir_api_base: str = task_cfg.get("fhir_api_base", "http://localhost:8080/fhir/")

        # Build id → original dataset index mapping (integer, same as SkillCycleRunner)
        full_data = _load_required_json_list(Path(config["data"]["full"]), "full dataset")
        self._id_to_index: Dict[str, int] = {s["id"]: i for i, s in enumerate(full_data)}

        self.dev_data = _load_required_json_list(Path(config["data"]["dev"]), "dev split")
        self.val_data = _load_required_json_list(Path(config["data"]["val"]), "val split")

        self.task_client = TaskClient(
            name=task_cfg["name"],
            controller_address=task_cfg["controller_address"],
        )

        self.memory_path = self.run_dir / "memory.json"

        from src.typings.general import InstanceFactory
        base_agent = InstanceFactory(**config["agent"]).create()
        self.memory_aware_agent = MemoryAwareAgent(base_agent, self.memory_path)

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

        original_stdout = sys.stdout
        original_stderr = sys.stderr
        self._progress_stream = (
            original_stderr
            if tqdm is not None and getattr(original_stderr, "isatty", lambda: False)()
            else None
        )
        sys.stdout = log_file
        try:
            self._run_inner()
        finally:
            sys.stdout = original_stdout
            self._progress_stream = None
            log_file.close()

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
        is_correct = _score_result(sample, result, self.fhir_api_base)
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
            is_correct = _score_result(sample, result, self.fhir_api_base)
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
    # Test-set evaluation
    # ------------------------------------------------------------------

    def _eval_split_with_agent(self, agent, data: List[Dict], out_dir: Path, split_label: str = "test") -> float:
        from src.client.task import TaskError
        out_dir.mkdir(parents=True, exist_ok=True)
        total = len(data)
        entries: List[Optional[Dict]] = [None] * total

        def run_one(idx: int, sample: Dict):
            task_index = self._id_to_index[sample["id"]]
            for attempt in range(3):
                result = self.task_client.run_sample(task_index, agent)
                if result.error != TaskError.NOT_AVAILABLE.value:
                    break
                time.sleep(5 * (attempt + 1))
            is_correct = _score_result(sample, result, self.fhir_api_base)
            return idx, is_correct, result

        with ThreadPoolExecutor(max_workers=self.batch_concurrency) as pool:
            futures = {pool.submit(run_one, i, s): i for i, s in enumerate(data)}
            for future in as_completed(futures):
                idx, is_correct, result = future.result()
                entries[idx] = {
                    "sample_id": data[idx]["id"],
                    "is_correct": is_correct,
                    "status": result.output.status if result.output else result.error,
                }

        n_correct = sum(e["is_correct"] for e in entries if e)
        score = n_correct / total if total > 0 else 0.0

        with open(out_dir / "test_runs.jsonl", "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

        summary = {"split": split_label, "score": score, "n_correct": n_correct, "n_total": total}
        with open(out_dir / "test_score.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return score

    def _make_best_agent(self):
        if not self._best_memory_path.exists():
            return None
        from src.typings.general import InstanceFactory
        base_agent = InstanceFactory(**self.config["agent"]).create()
        return MemoryAwareAgent(base_agent, self._best_memory_path)

    def run_test_eval(self) -> None:
        data_cfg = self.config.get("data", {})
        test_path = data_cfg.get("test")
        id_test_path = data_cfg.get("id_test")

        if not test_path and not id_test_path:
            print("[TestEval] Skipped: no 'test' or 'id_test' split configured.")
            return

        best_agent = self._make_best_agent()
        if best_agent is None:
            print("[TestEval] No best checkpoint found.")

        for split_label, path in [("test", test_path), ("id_test", id_test_path)]:
            if not path:
                continue
            split_data = _load_required_json_list(Path(path), f"{split_label} split")
            print(f"\n[TestEval] Running {split_label} evaluation ({len(split_data)} samples)...")
            prefix = "id_test_eval" if split_label == "id_test" else "test_eval"

            if best_agent is not None:
                best_dir = self.run_dir / f"{prefix}_best"
                print(f"[TestEval] Best checkpoint → {best_dir}")
                best_score = self._eval_split_with_agent(best_agent, split_data, best_dir, split_label)
                print(f"[TestEval] {split_label} best: {best_score:.1%}")
            else:
                print(f"[TestEval] Skipping best-checkpoint eval for {split_label}.")

            baseline_dir = self.run_dir / f"{prefix}_baseline"
            if not (baseline_dir / "test_score.json").exists():
                from src.typings.general import InstanceFactory
                base_agent = InstanceFactory(**self.config["agent"]).create()
                print(f"[TestEval] Baseline → {baseline_dir}")
                baseline_score = self._eval_split_with_agent(base_agent, split_data, baseline_dir, split_label)
                print(f"[TestEval] {split_label} baseline: {baseline_score:.1%}")
            else:
                print(f"[TestEval] {split_label} baseline already computed; skipping.")

        self._write_test_scores_summary()

    def _write_test_scores_summary(self) -> None:
        summary = {}
        for key in ("test_eval_best", "test_eval_baseline", "id_test_eval_best", "id_test_eval_baseline"):
            f = self.run_dir / key / "test_score.json"
            if f.exists():
                summary[key] = json.loads(f.read_text())
        with open(self.run_dir / "test_scores.json", "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)

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
    after a full batch. Dev samples are run one at a time; val evaluation is still
    parallelised via the inherited _evaluate_val.
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
