"""
FHIRBatchMemoryCycleRunner / FHIRMemoryCycleRunner — memory-based comparators to the FHIR
skill-learning cycle.

FHIRBatchMemoryCycleRunner: runs dev samples in parallel batches; updates memory after each batch.
FHIRMemoryCycleRunner: sequential variant matching the original MedAgentBench-v2 paper — updates
    memory immediately after each individual failing sample.

Both inject correction bullets into the agent via create_memory_aware_fhir_agent.
"""
from __future__ import annotations

import copy
import datetime
import json
import logging
import os
import random
import re
import shutil
import signal
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from core_utils import curate_input_dataset, parse_outputs

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

import pandas as pd

from .agent import (
    LiteLLMAgent,
    format_agent_actions,
    serialize_message,
)
from .evaluator import FHIRSampleEvaluator


# ---------------------------------------------------------------------------
# Memory-aware agent factory
# ---------------------------------------------------------------------------

def _render_memory(memory_path: Path) -> str:
    if not memory_path.exists():
        return ""
    try:
        bullets = json.loads(memory_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not bullets:
        return ""
    lines = ["<memory>", "Correction notes from past experience:"]
    lines += [f"- {b}" for b in bullets]
    lines.append("</memory>")
    return "\n".join(lines)


def create_memory_aware_fhir_agent(
    *,
    agent_strategy: str,
    model: str,
    base_url: Optional[str],
    verbose: bool,
    memory_path: Path,
    timeout: int = 20,
    max_retries: int = 3,
    max_tokens: int = 65536,
):
    """Create a FHIR agent that injects the current memory block into system_msg."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
    from core_utils import create_agent

    agent = create_agent(
        agent_strategy,
        model,
        verbose=verbose,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        max_tokens=max_tokens,
    )
    memory_block = _render_memory(memory_path)
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


# ---------------------------------------------------------------------------
# Memory updater (self-contained copy for FHIR)
# ---------------------------------------------------------------------------

def _extract_fenced_payload(text: str) -> Optional[str]:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text or "", re.DOTALL)
    return match.group(1).strip() if match else None


def _extract_json_array(text: str) -> List[Any]:
    candidates = []
    fenced = _extract_fenced_payload(text or "")
    if fenced:
        candidates.append(fenced)
    candidates.append(text or "")
    for candidate in candidates:
        start = candidate.find("[")
        if start == -1:
            continue
        try:
            data = json.loads(candidate[start:])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []


def _render_memory_block(bullets: List[str]) -> str:
    if not bullets:
        return "<memory>\n</memory>"
    lines = ["<memory>", "Correction notes from past experience:"]
    lines += [f"- {b}" for b in bullets]
    lines.append("</memory>")
    return "\n".join(lines)


def _format_fhir_agent_response(entry: Dict) -> str:
    task_result = entry.get("task_result")
    if task_result is not None:
        reported = task_result.get("reported_answer") if isinstance(task_result, dict) else task_result
        if reported is not None:
            return str(reported)[:1000]
    history = entry.get("history") or []
    for msg in reversed(history):
        if msg.get("role") in ("agent", "assistant"):
            content = str(msg.get("content", "") or "").strip()
            if content:
                return content[:1000]
    return "(no response captured)"


def _format_fhir_eval_output(entry: Dict) -> str:
    ground_truth = entry.get("ground_truth")
    is_correct = entry.get("is_correct", False)
    parts = []
    if ground_truth is not None:
        parts.append(f"ref_sol: {ground_truth}")
    parts.append(str(is_correct))
    return "\n".join(parts)


class _MemoryUpdater:
    def __init__(self, agent: LiteLLMAgent, max_bullets: int = 20) -> None:
        self.agent = agent
        self.max_bullets = max_bullets

    def propose_one(self, entry: Dict, current_bullets: List[str]) -> Optional[str]:
        instruction = str(entry.get("instruction", "") or entry.get("sample_id", ""))
        agent_response = _format_fhir_agent_response(entry)
        eval_output = _format_fhir_eval_output(entry)
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
            f"<task_description>\nInstruction:\n{instruction}\n</task_description>\n\n"
            f"<agent_response>\n{agent_response}\n</agent_response>\n\n"
            f"<eval_output>\n{eval_output}\n</eval_output>\n\n"
            f"<current_prompt>\n{current_prompt}\n</current_prompt>"
        )
        try:
            response = self.agent.inference([{"role": "user", "content": prompt}])
            bullet = response.strip()
            if bullet:
                print(f"[MemoryUpdater] new note: {bullet[:120]}")
                return bullet
        except Exception as e:
            print(f"[MemoryUpdater] propose_one failed: {e}")
        return None

    def propose(self, failing_entries: List[Dict], current_bullets: List[str]) -> List[str]:
        if not failing_entries:
            return []
        new_bullets: List[str] = []
        for entry in failing_entries:
            bullet = self.propose_one(entry, current_bullets + new_bullets)
            if bullet:
                new_bullets.append(bullet)
        return new_bullets

    def condense(self, bullets: List[str]) -> List[str]:
        target = max(10, self.max_bullets // 2)
        bullets_text = "\n".join(f"- {b}" for b in bullets)
        prompt = (
            f"The following memory list has {len(bullets)} entries. "
            f"Please condense it to at most {target} entries by merging similar notes "
            "and keeping only the most impactful ones. Preserve the 'when asked...' format "
            "where applicable.\n\n"
            f"Current entries:\n{bullets_text}\n\n"
            f"Return ONLY a JSON array of at most {target} strings:\n"
            '["entry 1", "entry 2"]'
        )
        try:
            response = self.agent.inference([{"role": "user", "content": prompt}])
            condensed = _extract_json_array(response)
            result = [str(b).strip() for b in condensed if isinstance(b, str) and b.strip()]
            if result:
                print(f"[MemoryUpdater] condensed {len(bullets)} → {len(result)} entries")
                return result[:target]
        except Exception as e:
            print(f"[MemoryUpdater] condense failed: {e}")
        return bullets[:target]

    def update(self, memory_path: Path, failing_entries: List[Dict]) -> List[str]:
        current: List[str] = []
        if memory_path.exists():
            try:
                current = json.loads(memory_path.read_text(encoding="utf-8"))
            except Exception:
                current = []
        new_bullets = self.propose(failing_entries, current)
        updated = current + new_bullets
        memory_path.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return updated


# ---------------------------------------------------------------------------
# Data loading helper
# ---------------------------------------------------------------------------

def _load_samples(csv_path: Path, split_names, limit: Optional[int]) -> List[Dict]:
    df = pd.read_csv(csv_path)
    df = df[df["split"].isin(list(split_names))].copy()
    if limit:
        df = df.head(limit)
    df["question_with_context"] = curate_input_dataset(df, add_patient_fhir_id=True)
    return df.to_dict("records")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class FHIRBatchMemoryCycleRunner:
    def __init__(self, config: Dict, run_dir: Path) -> None:
        self.config = config
        self.run_dir = Path(run_dir)

        agent_cfg = config["agent"]
        self.agent_strategy = agent_cfg.get("strategy", "multi_turn_resource")
        self.agent_model = agent_cfg["model"]
        self.agent_base_url = agent_cfg.get("base_url")
        self.verbose_agent = bool(agent_cfg.get("verbose", False))
        self.agent_timeout = int(agent_cfg.get("timeout", 20))
        self.agent_max_retries = int(agent_cfg.get("max_retries", 3))
        self.agent_max_tokens = int(agent_cfg.get("max_tokens", 65536))

        if agent_cfg.get("project_id"):
            os.environ["VERTEXAI_PROJECT"] = str(agent_cfg["project_id"])
        if agent_cfg.get("location"):
            os.environ["VERTEXAI_LOCATION"] = str(agent_cfg["location"])

        updater_cfg = config.get("updater", {})
        self.updater_agent = LiteLLMAgent(
            model=updater_cfg.get("model", self.agent_model),
            base_url=updater_cfg.get("base_url", self.agent_base_url),
            temperature=float(updater_cfg.get("temperature", 0.0)),
            max_tokens=int(updater_cfg.get("max_tokens", 32768)),
            timeout=int(updater_cfg.get("timeout", 20)),
            max_retries=int(updater_cfg.get("max_retries", 3)),
        )

        eval_cfg = config.get("eval", {})
        self.evaluator = FHIRSampleEvaluator(
            model=eval_cfg.get("model", self.agent_model),
            base_url=eval_cfg.get("base_url", self.agent_base_url),
            cache_path=self.run_dir / "eval_cache.json",
            timeout=int(eval_cfg.get("timeout", 20)),
            max_retries=int(eval_cfg.get("max_retries", 3)),
            max_tokens=int(eval_cfg.get("max_tokens", 65536)),
        )

        cycle_cfg = config["cycle"]
        self.epochs = int(cycle_cfg.get("epochs", 3))
        self.update_every = int(cycle_cfg.get("update_every", 25))
        self.batch_concurrency = int(cycle_cfg.get("batch_concurrency", 4))
        self.run_baseline = bool(cycle_cfg.get("run_baseline", True))

        memory_cfg = config.get("memory", {})
        self.max_bullets = int(memory_cfg.get("max_bullets", 20))
        self.memory_path = self.run_dir / "memory.json"
        self.memory_updater = _MemoryUpdater(self.updater_agent, max_bullets=self.max_bullets)

        data_cfg = config["data"]
        csv_path = Path(data_cfg["csv"])
        self.dev_data = _load_samples(
            csv_path, data_cfg.get("dev_splits", ["train"]), data_cfg.get("dev_limit")
        )
        self.val_data = _load_samples(
            csv_path, data_cfg.get("val_splits", ["valid"]), data_cfg.get("val_limit")
        )

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
        sys.stderr = log_file
        previous_handlers = {}

        def log_signal(signum, frame):
            print(f"\n[FHIRMemoryCycle] terminated by signal {signum}", flush=True)
            self._write_state("terminated", signal=signum)
            raise SystemExit(128 + signum)

        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            try:
                previous_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, log_signal)
            except (AttributeError, ValueError):
                pass

        try:
            self._write_state("started")
            print("[FHIRMemoryCycle] run started", flush=True)
            self._run_inner()
            self._write_state("completed")
            print("[FHIRMemoryCycle] run completed", flush=True)
        except SystemExit as e:
            self._write_state("system_exit", code=e.code)
            log_file.flush()
            raise
        except BaseException:
            self._write_state("failed")
            print("[FHIRMemoryCycle] run failed", flush=True)
            traceback.print_exc(file=log_file)
            log_file.flush()
            raise
        finally:
            for signum, handler in previous_handlers.items():
                try:
                    signal.signal(signum, handler)
                except (AttributeError, ValueError):
                    pass
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            self._progress_stream = None
            log_file.close()

    def _write_state(self, phase: str, **fields) -> None:
        state = {
            "phase": phase,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        state.update(fields)
        try:
            path = self.run_dir / "run_state.json"
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
            tmp.replace(path)
        except Exception:
            pass

    def _progress(self, iterable, *, total=None, desc="", leave=False):
        if tqdm is None or self._progress_stream is None:
            return iterable
        return tqdm(iterable, total=total, desc=desc, leave=leave,
                    file=self._progress_stream, dynamic_ncols=True)

    # ------------------------------------------------------------------
    # Inner loop
    # ------------------------------------------------------------------

    def _run_inner(self) -> None:
        print(f"[FHIRMemoryCycle] dev={len(self.dev_data)} val={len(self.val_data)}")

        val_scores_path = self.run_dir / "val_scores.json"
        val_scores: List[Dict] = []
        if self.resume and val_scores_path.exists():
            try:
                val_scores = json.loads(val_scores_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        if self.run_baseline:
            baseline_dir = self.run_dir / "baseline"
            baseline_score_path = baseline_dir / "val_score.json"
            if self.resume and baseline_score_path.exists():
                try:
                    s = json.loads(baseline_score_path.read_text(encoding="utf-8"))["score"]
                    print(f"[Resume] Baseline already done (val={s:.1%}), skipping")
                    if not any(e["epoch"] == -1 for e in val_scores):
                        val_scores.insert(0, {"epoch": -1, "score": s})
                except Exception:
                    pass
            else:
                baseline_dir.mkdir(exist_ok=True)
                score = self._evaluate_split(self.val_data, baseline_dir / "val_runs.jsonl", update_cycle=-1)
                print(f"[Baseline] Val: {score:.1%}")
                val_scores.append({"epoch": -1, "score": score})
                (baseline_dir / "val_score.json").write_text(
                    json.dumps({"epoch": -1, "score": score}, indent=2), encoding="utf-8"
                )
                val_scores_path.write_text(json.dumps(val_scores, indent=2), encoding="utf-8")

        for epoch in range(self.epochs):
            epoch_dir = self.run_dir / f"epoch_{epoch}"
            val_score_path = epoch_dir / "val_score.json"
            if self.resume and val_score_path.exists():
                try:
                    s = json.loads(val_score_path.read_text(encoding="utf-8"))["score"]
                    print(f"[Resume] Epoch {epoch} already done (val={s:.1%}), skipping")
                    if not any(e["epoch"] == epoch for e in val_scores):
                        val_scores.append({"epoch": epoch, "score": s})
                    if s > self._best_val_score:
                        self._best_val_score = s
                        self._best_checkpoint_label = epoch
                except Exception:
                    pass
                continue
            print(f"\n{'='*60}\n  EPOCH {epoch}\n{'='*60}")
            epoch_dir.mkdir(exist_ok=True)
            entries = self._run_epoch(epoch, epoch_dir)
            val_score = self._evaluate_split(self.val_data, epoch_dir / "val_runs.jsonl", update_cycle=epoch)
            val_scores.append({"epoch": epoch, "score": val_score})
            (epoch_dir / "val_score.json").write_text(
                json.dumps({"epoch": epoch, "score": val_score}, indent=2), encoding="utf-8"
            )
            val_scores_path.write_text(json.dumps(val_scores, indent=2), encoding="utf-8")
            print(f"[Epoch {epoch}] Val: {val_score:.1%}")
            self._maybe_update_best_checkpoint(val_score, epoch)

        final_bullets = []
        if self.memory_path.exists():
            try:
                final_bullets = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        print(f"[FHIRMemoryCycle] complete. Final memory: {len(final_bullets)} bullet(s)")

    def _run_epoch(self, epoch: int, epoch_dir: Path) -> List[Dict]:
        rng = random.Random(epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)
        batches = [dev[i:i + self.update_every] for i in range(0, len(dev), self.update_every)]
        print(f"[Epoch {epoch}] {len(dev)} dev samples, {len(batches)} batches")

        all_entries: List[Dict] = []
        updates: List[Dict] = []
        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        dev_runs_path.touch(exist_ok=True)

        for batch_id, batch in enumerate(batches):
            current_bullets: List[str] = []
            if self.memory_path.exists():
                try:
                    current_bullets = json.loads(self.memory_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            memory_version_before = len(current_bullets)

            print(f"  Batch {batch_id}/{len(batches)-1}: {len(batch)} samples "
                  f"(memory={memory_version_before} bullets)")

            batch_entries = self._run_samples(batch, update_cycle=batch_id, append_path=dev_runs_path)
            all_entries.extend(batch_entries)
            n_correct = sum(e["is_correct"] for e in batch_entries)
            print(f"  Batch score: {n_correct}/{len(batch_entries)}")

            failing_entries = [e for e in batch_entries if not e["is_correct"] and not e.get("error")]
            print(f"  Updating memory from {len(failing_entries)} failing trace(s)...")
            updated_bullets = self.memory_updater.update(self.memory_path, failing_entries)

            updates.append({
                "epoch": epoch,
                "update_cycle": batch_id,
                "batch_size": len(batch),
                "batch_correct": n_correct,
                "n_failing": len(failing_entries),
                "new_bullets": updated_bullets[memory_version_before:],
                "memory_size": len(updated_bullets),
            })
            (epoch_dir / "memory_updates.json").write_text(
                json.dumps(updates, indent=2), encoding="utf-8"
            )

        return all_entries

    def run_test_eval(self) -> None:
        data_cfg = self.config.get("data", {})
        test_splits = data_cfg.get("test_splits")
        if not test_splits:
            print("[TestEval] Skipped: no 'test_splits' configured.")
            return

        csv_path = Path(data_cfg["csv"])
        test_data = _load_samples(csv_path, test_splits, data_cfg.get("test_limit"))
        print(f"\n[TestEval] Running test set evaluation ({len(test_data)} samples)...")

        def _write_score(out_dir: Path, entries: List[Dict]) -> float:
            n_correct = sum(bool(e.get("is_correct")) for e in entries)
            score = n_correct / len(entries) if entries else 0.0
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_dir / "test_score.json", "w", encoding="utf-8") as f:
                json.dump({"split": "id_test", "score": score, "n_correct": n_correct, "n_total": len(entries)}, f, indent=2)
            return score

        if self._best_memory_path.exists():
            best_dir = self.run_dir / "id_test_eval_best"
            print(f"[TestEval] Best memory snapshot → {best_dir}")
            best_dir.mkdir(parents=True, exist_ok=True)
            orig_memory_path = self.memory_path
            self.memory_path = self._best_memory_path
            try:
                best_entries = self._run_samples(test_data, update_cycle=-1, append_path=best_dir / "test_runs.jsonl")
            finally:
                self.memory_path = orig_memory_path
            best_score = _write_score(best_dir, best_entries)
            print(f"[TestEval] ID test best: {best_score:.1%}")
        else:
            print("[TestEval] No best checkpoint; skipping best-checkpoint eval.")

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
    # Sample execution
    # ------------------------------------------------------------------

    def _evaluate_split(self, samples: List[Dict], path: Path, update_cycle: int) -> float:
        print(f"[Eval] evaluating {len(samples)} samples -> {path}")
        entries = self._run_samples(samples, update_cycle=update_cycle, append_path=path)
        if not entries:
            return 0.0
        return sum(e["is_correct"] for e in entries) / len(entries)

    def _run_samples(
        self,
        samples: List[Dict],
        update_cycle: int,
        append_path: Optional[Path] = None,
    ) -> List[Dict]:
        if append_path:
            append_path.parent.mkdir(parents=True, exist_ok=True)
            append_path.touch(exist_ok=True)

        results: List[Dict] = []
        with ThreadPoolExecutor(max_workers=self.batch_concurrency) as executor:
            futures = {
                executor.submit(self._run_one, sample, update_cycle): sample
                for sample in samples
            }
            for future in self._progress(as_completed(futures), total=len(futures), desc="FHIR samples"):
                sample = futures[future]
                try:
                    entry = future.result()
                except BaseException as e:
                    error_trace = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    print(
                        f"[FHIRMemoryCycle] sample failed for {sample.get('question_id')}: "
                        f"{type(e).__name__}: {e}",
                        flush=True,
                    )
                    entry = {
                        "sample_id": sample.get("question_id"),
                        "instruction": sample.get("question"),
                        "query_type": sample.get("template") or sample.get("main_table_name"),
                        "is_correct": False,
                        "update_cycle": update_cycle,
                        "status": "runner_error",
                        "error": f"{type(e).__name__}: {e}",
                        "ground_truth": sample.get("true_answer"),
                        "task_result": {},
                        "agent_actions": [],
                        "history": [],
                        "failure_tags": [
                            str(x)
                            for x in [sample.get("template"), sample.get("main_table_name")]
                            if x
                        ],
                    }
                results.append(entry)
                if append_path:
                    with open(append_path, "a", encoding="utf-8") as f:
                        safe = {k: v for k, v in entry.items() if not k.startswith("_")}
                        f.write(json.dumps(safe, default=str) + "\n")

        results.sort(key=lambda e: str(e["sample_id"]))
        n_correct = sum(bool(e.get("is_correct")) for e in results)
        print(f"[RunSamples] finished {len(results)} samples score={n_correct}/{len(results)}", flush=True)
        return results

    def _run_one(self, sample: Dict, update_cycle: int) -> Dict:
        import tools.cache as cache_module
        cache_module.CACHE_ENABLED = bool(self.config.get("agent", {}).get("enable_cache", True))

        agent = create_memory_aware_fhir_agent(
            agent_strategy=self.agent_strategy,
            model=self.agent_model,
            base_url=self.agent_base_url,
            verbose=self.verbose_agent,
            memory_path=self.memory_path,
            timeout=self.agent_timeout,
            max_retries=self.agent_max_retries,
            max_tokens=self.agent_max_tokens,
        )
        try:
            raw_output = agent.run(sample["question_with_context"])
            parsed = parse_outputs(raw_output)
        except Exception as e:
            raw_output = {"error": str(e), "trace": []}
            parsed = {
                "agent_answer": None,
                "agent_fhir_resources": None,
                "trace": [],
                "usage": None,
                "error": str(e),
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


class FHIRMemoryCycleRunner(FHIRBatchMemoryCycleRunner):
    """Sequential variant matching the original MedAgentBench-v2 paper.

    Memory is updated immediately after each individual failing sample rather than
    after a full batch. Dev samples are run one at a time; val evaluation is still
    parallelised via the inherited _evaluate_split.
    """

    def _run_epoch(self, epoch: int, epoch_dir: Path) -> List[Dict]:
        rng = random.Random(epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)
        print(f"[Epoch {epoch}] {len(dev)} dev samples — sequential, update per failure")

        all_entries: List[Dict] = []
        update_events: List[Dict] = []
        n_updates = 0
        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        dev_runs_path.touch(exist_ok=True)

        for sample_idx, sample in enumerate(dev):
            current_bullets: List[str] = []
            if self.memory_path.exists():
                try:
                    current_bullets = json.loads(self.memory_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            memory_version_before = len(current_bullets)

            try:
                entry = self._run_one(sample, update_cycle=n_updates)
            except BaseException as e:
                error_trace = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                print(f"[FHIRMemoryCycle] sample failed for {sample.get('question_id')}: {e}")
                entry = {
                    "sample_id": sample.get("question_id"),
                    "instruction": sample.get("question"),
                    "query_type": sample.get("template") or sample.get("main_table_name"),
                    "is_correct": False,
                    "update_cycle": n_updates,
                    "status": "runner_error",
                    "error": f"{type(e).__name__}: {e}",
                    "ground_truth": sample.get("true_answer"),
                    "task_result": {},
                    "agent_actions": [],
                    "history": [],
                    "failure_tags": [
                        str(x) for x in [sample.get("template"), sample.get("main_table_name")] if x
                    ],
                }
            all_entries.append(entry)
            with open(dev_runs_path, "a", encoding="utf-8") as f:
                safe = {k: v for k, v in entry.items() if not k.startswith("_")}
                f.write(json.dumps(safe, default=str) + "\n")

            if not entry.get("is_correct") and not entry.get("error"):
                updated_bullets = self.memory_updater.update(self.memory_path, [entry])
                update_events.append({
                    "epoch": epoch,
                    "sample_idx": sample_idx,
                    "sample_id": entry["sample_id"],
                    "memory_version_before": memory_version_before,
                    "new_bullets": updated_bullets[memory_version_before:],
                    "memory_size": len(updated_bullets),
                })
                n_updates += 1

        (epoch_dir / "memory_updates.json").write_text(
            json.dumps(update_events, indent=2), encoding="utf-8"
        )
        n_correct = sum(bool(e.get("is_correct")) for e in all_entries)
        print(f"[Epoch {epoch}] Dev score: {n_correct}/{len(all_entries)} | Updates: {n_updates}")
        return all_entries
