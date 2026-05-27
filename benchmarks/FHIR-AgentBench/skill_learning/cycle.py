import argparse
import datetime
import io
import json
import random
import shutil
import os
import signal
import sys
import logging
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import yaml
from fhir_agent_preset import apply_backend

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from core_utils import curate_input_dataset, parse_outputs

from .agent import (
    LiteLLMAgent,
    create_skill_aware_fhir_agent,
    format_agent_actions,
    serialize_message,
)
from .evaluator import FHIRSampleEvaluator
from .repository import SkillRepository
from .updater import SkillUpdater


class _TeeStream(io.TextIOBase):
    def __init__(self, primary, secondary):
        self._primary = primary
        self._secondary = secondary

    def write(self, s):
        self._primary.write(s)
        self._secondary.write(s)
        return len(s)

    def flush(self):
        self._primary.flush()
        self._secondary.flush()

    @property
    def encoding(self):
        return getattr(self._primary, "encoding", "utf-8")


def _load_samples(csv_path: Path, split_names: Iterable[str], limit: Optional[int]) -> List[Dict]:
    df = pd.read_csv(csv_path)
    df = df[df["split"].isin(list(split_names))].copy()
    if limit:
        df = df.head(limit)
    df["question_with_context"] = curate_input_dataset(df, add_patient_fhir_id=True)
    return df.to_dict("records")


def _compute_skill_effectiveness(
    entries: List[Dict], prev_results: Optional[Dict[str, bool]]
) -> Dict[str, Dict[str, int]]:
    stats: Dict[str, Dict[str, int]] = {}
    for entry in entries:
        sid = str(entry.get("sample_id"))
        now = bool(entry.get("is_correct"))
        prev = prev_results.get(sid) if prev_results else None
        for skill in entry.get("skill_snapshot_before") or []:
            name = skill.get("name")
            if not name or name == "skeleton":
                continue
            stats.setdefault(name, {"fixes": 0, "regressions": 0, "runs": 0})
            stats[name]["runs"] += 1
            if prev is not None:
                if not prev and now:
                    stats[name]["fixes"] += 1
                elif prev and not now:
                    stats[name]["regressions"] += 1
    return stats


class FHIRSkillCycleRunner:
    def __init__(self, config: Dict, run_dir: Path) -> None:
        self.config = config
        self.run_dir = Path(run_dir)
        self.output_dir = self.run_dir

        agent_cfg = config["agent"]
        self.agent_strategy = agent_cfg.get("strategy", "multi_turn_resource")
        self.agent_model = agent_cfg["model"]
        self.agent_base_url = agent_cfg.get("base_url")
        self.verbose_agent = bool(agent_cfg.get("verbose", False))
        self.agent_timeout = int(agent_cfg.get("timeout", 20))
        self.agent_max_retries = int(agent_cfg.get("max_retries", 3))
        self.agent_max_tokens = int(agent_cfg.get("max_tokens", 65536))
        self.agent_sample_timeout = agent_cfg.get("sample_timeout")  # wall-clock limit per sample (seconds)
        
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
        self.grpo_k = int(cycle_cfg.get("grpo_k", 4))
        self.grpo_eval_n = int(cycle_cfg.get("grpo_eval_n", 20))
        self.run_baseline = bool(cycle_cfg.get("run_baseline", True))
        self.seed: int = int(cycle_cfg.get("seed", 0))
        self.max_proposals = int(cycle_cfg.get("max_proposals", 1))
        self.max_learned_skills = int(cycle_cfg.get("max_learned_skills", 10))
        self.non_learnable_labels = [
            s.lower() for s in cycle_cfg.get("non_learnable_labels", [])
        ]

        data_cfg = config["data"]
        csv_path = Path(data_cfg["csv"])
        self.dev_data = _load_samples(csv_path, data_cfg.get("dev_splits", ["train"]), data_cfg.get("dev_limit"))
        self.val_data = _load_samples(csv_path, data_cfg.get("val_splits", ["valid"]), data_cfg.get("val_limit"))

        skills_cfg = config["skills"]
        self.skill_repo = SkillRepository(
            base_dir=Path(skills_cfg["base_dir"]),
            learned_dir=self.run_dir / "skills" / "learned",
        )
        self.updater = SkillUpdater(
            self.updater_agent,
            max_proposals=self.max_proposals,
            max_learned_skills=self.max_learned_skills,
        )
        self._progress_stream = None
        self.resume = bool(config.get("_resume", False))

        # Best-checkpoint tracking: snapshot learned/ whenever val improves
        self._best_val_score: float = 0.0
        self._best_checkpoint_label: Any = None
        self._best_skills_dir: Path = self.run_dir / "skills" / "best"

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
        
        # NOTE: Hide background scores, skill proposals, and regression scores from CLI
        # by defaulting sys.stdout to log_file.
        # But we will temporarily swap it back during _update_skills trace generation!
        sys.stdout = log_file
        sys.stderr = log_file
        previous_handlers = {}

        def log_signal(signum, frame):
            print(f"\n[FHIRSkillCycle] terminated by signal {signum}", flush=True)
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
            print("[FHIRSkillCycle] run started", flush=True)
            self._run_inner()
            self._write_state("completed")
            restored = self._restore_best_checkpoint()
            if restored:
                print(
                    f"[BestCheckpoint] Final skills restored from best checkpoint: "
                    f"epoch={self._best_checkpoint_label}, val={self._best_val_score:.1%}"
                )
            print("[FHIRSkillCycle] run completed", flush=True)
        except SystemExit as e:
            current_state = {}
            try:
                state_path = self.run_dir / "run_state.json"
                if state_path.exists():
                    current_state = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                current_state = {}
            if current_state.get("phase") != "terminated":
                self._write_state("system_exit", code=e.code)
                print(f"[FHIRSkillCycle] system exit: {e.code}", flush=True)
            log_file.flush()
            raise
        except BaseException:
            self._write_state("failed")
            print("[FHIRSkillCycle] run failed", flush=True)
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

    def run_test_eval(self) -> None:
        data_cfg = self.config.get("data", {})
        test_splits = data_cfg.get("test_splits")
        if not test_splits:
            print("[TestEval] Skipped: no 'test_splits' configured.")
            return

        csv_path = Path(data_cfg["csv"])
        test_data = _load_samples(csv_path, test_splits, data_cfg.get("test_limit"))
        print(f"\n[TestEval] Running ID test evaluation ({len(test_data)} samples)...")

        def _write_score(out_dir: Path, entries: List[Dict]) -> float:
            n_correct = sum(bool(e.get("is_correct")) for e in entries)
            score = n_correct / len(entries) if entries else 0.0
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_dir / "test_score.json", "w", encoding="utf-8") as f:
                json.dump({"split": "id_test", "score": score, "n_correct": n_correct, "n_total": len(entries)}, f, indent=2)
            return score

        if self._best_skills_dir.exists():
            best_repo = SkillRepository(
                base_dir=self.skill_repo.base_dir,
                learned_dir=self._best_skills_dir,
            )
            best_dir = self.run_dir / "id_test_eval_best"
            print(f"[TestEval] Best checkpoint (skills/best/) → {best_dir}")
            best_dir.mkdir(parents=True, exist_ok=True)
            best_entries = self._run_samples(test_data, best_repo, update_cycle=-1, append_path=best_dir / "test_runs.jsonl")
            best_score = _write_score(best_dir, best_entries)
            print(f"[TestEval] ID test best: {best_score:.1%}")
        else:
            print("[TestEval] No best checkpoint; skipping best-checkpoint eval.")

    def run_baseline_test_eval(self) -> None:
        data_cfg = self.config.get("data", {})
        test_splits = data_cfg.get("test_splits")
        if not test_splits:
            print("[BaselineTestEval] Skipped: no 'test_splits' configured.")
            return

        baseline_dir = self.run_dir / "id_test_eval_baseline"
        if (baseline_dir / "test_score.json").exists():
            print("[BaselineTestEval] Already complete; skipping.")
            return

        csv_path = Path(data_cfg["csv"])
        test_data = _load_samples(csv_path, test_splits, data_cfg.get("test_limit"))
        print(f"\n[BaselineTestEval] Running ID test baseline evaluation ({len(test_data)} samples)...")
        baseline_dir.mkdir(parents=True, exist_ok=True)
        empty_repo = SkillRepository(
            base_dir=self.skill_repo.base_dir,
            learned_dir=Path(tempfile.mkdtemp()) / "empty",
        )
        baseline_entries = self._run_samples(test_data, empty_repo, update_cycle=-1, append_path=baseline_dir / "test_runs.jsonl")
        n_correct = sum(bool(e.get("is_correct")) for e in baseline_entries)
        baseline_score = n_correct / len(baseline_entries) if baseline_entries else 0.0
        with open(baseline_dir / "test_score.json", "w", encoding="utf-8") as f:
            json.dump({"split": "id_test", "score": baseline_score, "n_correct": n_correct, "n_total": len(baseline_entries)}, f, indent=2)
        print(f"[BaselineTestEval] ID test baseline (no skills): {baseline_score:.1%}")

    def _maybe_update_best_checkpoint(self, val_score: float, label: Any) -> None:
        """Snapshot learned/ to skills/best/ whenever val improves."""
        if val_score > self._best_val_score:
            self._best_val_score = val_score
            self._best_checkpoint_label = label
            if self._best_skills_dir.exists():
                shutil.rmtree(self._best_skills_dir)
            shutil.copytree(self.skill_repo.learned_dir, self._best_skills_dir)
            print(
                f"[BestCheckpoint] New best: epoch={label}, val={val_score:.1%} — snapshot saved"
            )

    def _restore_best_checkpoint(self) -> bool:
        """Replace learned/ with the best-checkpoint snapshot. Returns True if restored."""
        if not self._best_skills_dir.exists():
            return False
        if self.skill_repo.learned_dir.exists():
            shutil.rmtree(self.skill_repo.learned_dir)
        shutil.copytree(self._best_skills_dir, self.skill_repo.learned_dir)
        return True

    def _write_state(self, phase: str, **fields) -> None:
        state = {
            "phase": phase,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        state.update(fields)
        try:
            path = self.run_dir / "run_state.json"
            tmp_path = path.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
            tmp_path.replace(path)
        except Exception:
            pass

    def _progress(self, iterable, *, total: Optional[int] = None, desc: str = "", leave: bool = False):
        if tqdm is None or self._progress_stream is None:
            return iterable
        return tqdm(iterable, total=total, desc=desc, leave=leave, file=self._progress_stream, dynamic_ncols=True)

    def _run_inner(self) -> None:
        print(f"[FHIRSkillCycle] dev={len(self.dev_data)} val={len(self.val_data)} strategy={self.agent_strategy}")
        
        val_scores = []
        if self.run_baseline:
            baseline_dir = self.run_dir / "baseline"
            baseline_dir.mkdir(exist_ok=True)
            score = self._evaluate_split(self.val_data, baseline_dir / "val_runs.jsonl", update_cycle=-1)
            print(f"[Baseline] Val: {score:.1%}")
            val_scores.append({"epoch": -1, "score": score})
            (self.run_dir / "val_scores.json").write_text(json.dumps(val_scores, indent=2), encoding="utf-8")

        prev_taxonomy: Dict[str, str] = {}
        prev_results: Optional[Dict[str, bool]] = None
        for epoch in range(self.epochs):
            print(f"\n{'=' * 60}\n  EPOCH {epoch}\n{'=' * 60}")
            epoch_dir = self.run_dir / f"epoch_{epoch}"
            epoch_dir.mkdir(exist_ok=True)
            entries, prev_taxonomy = self._run_epoch(epoch, epoch_dir, prev_results, prev_taxonomy)
            prev_results = {str(e["sample_id"]): bool(e["is_correct"]) for e in entries}
            val_score = self._evaluate_split(self.val_data, epoch_dir / "val_runs.jsonl", update_cycle=epoch)
            val_scores.append({"epoch": epoch, "score": val_score})
            (epoch_dir / "val_score.json").write_text(
                json.dumps({"epoch": epoch, "score": val_score}, indent=2),
                encoding="utf-8",
            )
            (self.run_dir / "val_scores.json").write_text(json.dumps(val_scores, indent=2), encoding="utf-8")
            print(f"[Epoch {epoch}] Val: {val_score:.1%}")
            self._maybe_update_best_checkpoint(val_score, epoch)

    def _run_epoch(
        self,
        epoch: int,
        epoch_dir: Path,
        prev_results: Optional[Dict[str, bool]],
        prev_taxonomy: Dict[str, str],
    ) -> Tuple[List[Dict], Dict[str, str]]:
        rng = random.Random(self.seed * 1_000_000 + epoch)
        dev = self.dev_data[:]
        rng.shuffle(dev)
        batches = [dev[i:i + self.update_every] for i in range(0, len(dev), self.update_every)]
        print(f"[Epoch {epoch}] {len(dev)} dev samples, {len(batches)} batches")

        all_entries: List[Dict] = []
        updates_path = epoch_dir / "skill_updates.json"
        updates: List[Dict] = []
        if self.resume and updates_path.exists():
            try:
                updates = json.loads(updates_path.read_text(encoding="utf-8"))
                for event in updates:
                    prev_taxonomy.update(event.get("new_failure_labels", {}))
            except Exception as e:
                print(f"[Resume] could not load {updates_path}: {e}")
                updates = []
        completed_update_cycles = {
            int(event.get("update_cycle"))
            for event in updates
            if event.get("update_cycle") is not None
        }
        dev_runs_path = epoch_dir / "dev_runs.jsonl"
        for batch_id, batch in enumerate(self._progress(batches, total=len(batches), desc=f"Epoch {epoch} batches")):
            print(f"  Batch {batch_id}/{len(batches)-1}: {len(batch)} samples")
            batch_entries = self._run_samples(
                batch,
                self.skill_repo,
                update_cycle=batch_id,
                append_path=dev_runs_path,
            )
            all_entries.extend(batch_entries)
            print(f"  Batch score: {sum(e['is_correct'] for e in batch_entries)}/{len(batch_entries)}")

            if self.resume and batch_id in completed_update_cycles:
                print(f"  [Resume] update_cycle={batch_id} already has skill update event; skipping update")
            else:
                event = self._update_skills(
                    batch_entries=batch_entries,
                    all_entries=all_entries,
                    prev_results=prev_results,
                    prev_taxonomy=prev_taxonomy,
                    epoch=epoch,
                    update_cycle=batch_id,
                )
                if event:
                    updates.append(event)
                    prev_taxonomy.update(event.get("new_failure_labels", {}))
                    completed_update_cycles.add(batch_id)
            updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

        return all_entries, prev_taxonomy

    def _update_skills(
        self,
        *,
        batch_entries: List[Dict],
        all_entries: List[Dict],
        prev_results: Optional[Dict[str, bool]],
        prev_taxonomy: Dict[str, str],
        epoch: int,
        update_cycle: int,
    ) -> Optional[Dict]:
        failing = [e for e in batch_entries if not e.get("is_correct")]
        if not failing:
            print("  No failures in batch; skipping update.")
            return None

        sample_to_label, new_labels = self.updater.classify_failures(failing, prev_taxonomy)
        for e in failing:
            if e.get("status") == "sample_timeout":
                sample_to_label[str(e.get("sample_id", ""))] = "sample_timeout"

        # Drop infrastructure failures (timeouts, runner crashes, service errors) so the
        # updater never wastes proposals on things that aren't skill gaps.
        if self.non_learnable_labels:
            learnable_failing = [
                e for e in failing
                if not any(
                    pat in sample_to_label.get(str(e.get("sample_id", "")), "").lower()
                    for pat in self.non_learnable_labels
                )
            ]
            n_skipped = len(failing) - len(learnable_failing)
            if n_skipped:
                learnable_ids = {str(e.get("sample_id", "")) for e in learnable_failing}
                sample_to_label = {
                    sid: lbl for sid, lbl in sample_to_label.items() if sid in learnable_ids
                }
                print(f"  [SkillFilter] excluded {n_skipped} non-learnable failures from proposal pool")
                failing = learnable_failing
            if not failing:
                print("  No learnable failures after filtering; skipping update.")
                event = {
                    "epoch": epoch,
                    "update_cycle": update_cycle,
                    "new_failure_labels": new_labels,
                    "applied": [],
                    "raw_proposals": [],
                    "grpo": [],
                    "reason": "all_failures_non_learnable",
                }
                return event

        diagnosis = self.updater.diagnose(failing, self.skill_repo, failure_labels=sample_to_label)
        effectiveness = _compute_skill_effectiveness(all_entries, prev_results)

        event = {
            "epoch": epoch,
            "update_cycle": update_cycle,
            "new_failure_labels": new_labels,
            "applied": [],
            "raw_proposals": [],
            "grpo": [],
        }

        # Only include learnable failing entries in proposal groups so non-learnable
        # failures don't become an "unlabeled" group that wastes proposal budget.
        _learnable_ids = {str(e.get("sample_id", "")) for e in failing}
        _batch_for_proposals = [
            e for e in batch_entries
            if e.get("is_correct") or str(e.get("sample_id", "")) in _learnable_ids
        ]
        proposal_groups = self._group_entries_by_failure_mode(_batch_for_proposals, sample_to_label)
        print(
            "  [ProposalRanking] failure groups: "
            + ", ".join(f"{label}({len(entries)})" for label, entries in proposal_groups)
        )

        candidates = []
        raw_proposals = []
        for k in range(self.grpo_k):
            label, group_entries = proposal_groups[k % len(proposal_groups)]
            group_ids = {
                str(e.get("sample_id", ""))
                for e in group_entries
                if not e.get("is_correct", False)
            }
            group_diagnosis = {
                sid: d for sid, d in diagnosis.items() if sid in group_ids
            }
            other_failing = [
                dict(e, _failure_label=sample_to_label.get(str(e.get("sample_id", "")), "unknown"))
                for e in failing
                if str(e.get("sample_id", "")) not in group_ids
            ]
            raw = self.updater.propose(
                group_entries,
                self.skill_repo,
                prev_results=prev_results,
                skill_effectiveness=effectiveness,
                failure_mode=label,
                diagnosis=group_diagnosis or None,
                other_failing=other_failing or None,
            )
            raw_proposals.extend(raw)
            valid = self.updater.validate(raw, self.skill_repo)
            if valid:
                for proposal in valid:
                    candidates.append({
                        "label": label,
                        "group_entries": group_entries,
                        "proposal": proposal,
                    })

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            proposal = candidate["proposal"]
            key = (
                proposal["action"],
                proposal["name"],
                proposal.get("content", "")[:100],
            )
            if key in seen:
                continue
            seen.add(key)
            unique_candidates.append(candidate)

        print(
            f"  [ProposalRanking] {len(candidates)} proposals sampled, "
            f"{len(unique_candidates)} unique"
        )
        if not unique_candidates:
            event["raw_proposals"] = raw_proposals
            event["reason"] = "no_valid_proposals"
            return event

        rng = random.Random(self.seed * 1_000_000 + epoch * 1_000 + update_cycle)
        probe, probe_failing_ids = self._build_probe_set(
            all_entries=all_entries,
            prev_results=prev_results,
            epoch=epoch,
            update_cycle=update_cycle,
            rng=rng,
        )
        if not probe:
            print("  [ProposalRanking] skipping update: no probe data")
            event["raw_proposals"] = raw_proposals
            event["reason"] = "no_probe_data"
            return event
        n_failing = sum(1 for e in probe if str(e["sample_id"]) in probe_failing_ids)
        n_passing = len(probe) - n_failing
        print(
            f"  [ProposalRanking] probe set: {n_failing} failing + "
            f"{n_passing} passing = {len(probe)} samples"
        )
        baseline_entries = self._run_samples(
            [e["_sample"] for e in probe],
            self.skill_repo,
            update_cycle=update_cycle,
        )
        baseline_error_ids = {
            str(e.get("sample_id")) for e in baseline_entries if e.get("error")
        }
        baseline_fixes, baseline_regressions = self._count_probe_transitions(
            baseline_entries, probe_failing_ids
        )
        print(
            f"  [ProposalRanking] baseline probe: "
            f"{baseline_fixes} fixes, {baseline_regressions} regressions "
            f"(current skills, no proposal); "
            f"{len(baseline_error_ids)} pre-existing errors excluded from regression count"
        )

        best = None
        best_label = None
        best_group_entries: List[Dict] = []
        best_adjusted = 0
        best_stats = (0, 0)
        best_regressed_traces: List[Dict] = []
        candidate_logs = []
        for candidate_info in unique_candidates:
            label = candidate_info["label"]
            candidate = candidate_info["proposal"]
            try:
                print(
                    f"  [ProposalRanking] evaluating {len(probe)} "
                    f"probe samples for {candidate['action']}::{candidate['name']}"
                )
                raw_score, fixes, regressions, regressed_traces = self._eval_candidate(
                    candidate,
                    probe,
                    probe_failing_ids,
                    update_cycle,
                    baseline_error_ids,
                )
                adjusted = (
                    (fixes - baseline_fixes)
                    - (regressions - baseline_regressions)
                )
            except Exception as e:
                print(f"  [ProposalRanking] candidate failed: {e}")
                fixes = regressions = 0
                regressed_traces = []
                raw_score = adjusted = -1

            print(
                f"  [ProposalRanking] {candidate['action']}::{candidate['name']} -> "
                f"adjusted={adjusted:+d} raw={raw_score:+d} "
                f"(fixes={fixes} baseline_fixes={baseline_fixes}, "
                f"regressions={regressions} "
                f"baseline_regressions={baseline_regressions})"
            )
            candidate_logs.append({
                "failure_mode": label,
                "proposal": {k: v for k, v in candidate.items() if not k.startswith("_")},
                "net": adjusted,
                "score": adjusted,
                "raw_score": raw_score,
                "fixes": fixes,
                "regressions": regressions,
                "baseline_fixes": baseline_fixes,
                "baseline_regressions": baseline_regressions,
            })
            if adjusted > best_adjusted and regressions <= baseline_regressions:
                best = candidate
                best_label = label
                best_group_entries = candidate_info["group_entries"]
                best_adjusted = adjusted
                best_stats = (fixes, regressions)
                best_regressed_traces = regressed_traces

        if best is None:
            print(
                "  [ProposalRanking] no proposal met acceptance criteria "
                "(adjusted > 0 and regressions <= baseline regressions) — applying nothing"
            )
            event["raw_proposals"] = raw_proposals
            event["grpo"] = candidate_logs
            event["baseline_fixes"] = baseline_fixes
            event["baseline_regressions"] = baseline_regressions
            return event

        if best_regressed_traces:
            print(
                f"  [ContrastiveRevision] {len(best_regressed_traces)} regression(s) — "
                f"requesting targeted revision..."
            )
            raw_revisions = self.updater.revise(best, best_regressed_traces, self.skill_repo)
            revisions = self.updater.validate(raw_revisions, self.skill_repo)
            if revisions:
                revision = revisions[0]
                try:
                    raw_score, fixes, regressions, _ = self._eval_candidate(
                        revision,
                        probe,
                        probe_failing_ids,
                        update_cycle,
                        baseline_error_ids,
                    )
                    adjusted = (
                        (fixes - baseline_fixes)
                        - (regressions - baseline_regressions)
                    )
                    print(
                        f"  [ContrastiveRevision] {revision['action']}::{revision['name']} -> "
                        f"adjusted={adjusted:+d} (fixes={fixes}, regressions={regressions})"
                    )
                    candidate_logs.append({
                        "failure_mode": best_label,
                        "proposal": {
                            k: v for k, v in revision.items() if not k.startswith("_")
                        },
                        "net": adjusted,
                        "score": adjusted,
                        "raw_score": raw_score,
                        "fixes": fixes,
                        "regressions": regressions,
                        "baseline_fixes": baseline_fixes,
                        "baseline_regressions": baseline_regressions,
                        "contrastive_revision": True,
                    })
                    if adjusted > best_adjusted and regressions <= baseline_regressions:
                        print(
                            f"  [ContrastiveRevision] revision wins: "
                            f"adjusted={adjusted:+d} > {best_adjusted:+d}"
                        )
                        best = revision
                        best_adjusted = adjusted
                        best_stats = (fixes, regressions)
                    else:
                        print(
                            "  [ContrastiveRevision] revision did not meet acceptance criteria "
                            f"(adjusted={adjusted:+d}, best={best_adjusted:+d}, "
                            f"regressions={regressions}, baseline_regressions={baseline_regressions}), "
                            "keeping original"
                        )
                except Exception as e:
                    print(f"  [ContrastiveRevision] eval failed: {e}")
            else:
                print("  [ContrastiveRevision] revision failed validation")

        best["_provenance"] = {
            "epoch": epoch,
            "update_cycle": update_cycle,
            "failure_mode": best_label,
            "probe_score": best_adjusted,
            "fixes": best_stats[0],
            "regressions": best_stats[1],
            "baseline_fixes": baseline_fixes,
            "baseline_regressions": baseline_regressions,
            "triggering_sample_ids": [
                e["sample_id"] for e in best_group_entries if not e.get("is_correct")
            ][:10],
        }
        applied = self.updater.apply([best], self.skill_repo)
        print(
            f"  [ProposalRanking] winner: {best['action']}::{best['name']} "
            f"adjusted={best_adjusted:+d} "
            f"(fixes={best_stats[0]}, regressions={best_stats[1]})"
        )
        print(f"  [SkillUpdate] {best_label}: applied {len(applied)} edit(s)")

        event["applied"] = applied
        event["raw_proposals"] = raw_proposals
        event["grpo"] = candidate_logs
        event["baseline_fixes"] = baseline_fixes
        event["baseline_regressions"] = baseline_regressions
        return event

    def _eval_candidate(
        self,
        proposal: Dict,
        probe: List[Dict],
        probe_failing_ids: set,
        update_cycle: int,
        baseline_error_ids: set = frozenset(),
    ) -> Tuple[int, int, int, List[Dict]]:
        fork = self.skill_repo.fork()
        try:
            self.updater.apply([proposal], fork)
            probe_entries = self._run_samples(
                [e["_sample"] for e in probe],
                fork,
                update_cycle=update_cycle,
            )
            fixes, regressions = self._count_probe_transitions(
                probe_entries,
                probe_failing_ids,
                baseline_error_ids,
            )
            regressed_traces = [
                e for e in probe_entries
                if str(e.get("sample_id")) not in probe_failing_ids
                and not e.get("is_correct", False)
                and not (e.get("error") and str(e.get("sample_id")) in baseline_error_ids)
            ]
            return fixes - regressions, fixes, regressions, regressed_traces
        finally:
            fork.cleanup()

    @staticmethod
    def _count_probe_transitions(
        entries: List[Dict], probe_failing_ids: set, baseline_error_ids: set = frozenset()
    ) -> Tuple[int, int]:
        fixes = 0
        regressions = 0
        for entry in entries:
            sample_id = str(entry.get("sample_id"))
            if entry.get("error") and sample_id in baseline_error_ids:
                # Same sample errored in the baseline probe too — pre-existing
                # noise, not attributable to this skill candidate.
                continue
            is_correct = bool(entry.get("is_correct"))
            was_failing = sample_id in probe_failing_ids
            if was_failing and is_correct:
                fixes += 1
            elif not was_failing and not is_correct:
                regressions += 1
        return fixes, regressions

    @staticmethod
    def _group_entries_by_failure_mode(
        entries: List[Dict],
        labels: Dict[str, str],
    ) -> List[Tuple[str, List[Dict]]]:
        if not labels:
            return [("unknown", entries)]
        passing = [e for e in entries if e.get("is_correct", False)]
        groups: Dict[str, List[Dict]] = {}
        for entry in entries:
            if entry.get("is_correct", False):
                continue
            label = labels.get(str(entry.get("sample_id", "")), "unlabeled")
            groups.setdefault(label, []).append(entry)
        if not groups:
            return [("unknown", entries)]
        return [
            (label, group + passing)
            for label, group in sorted(groups.items(), key=lambda item: len(item[1]), reverse=True)
        ]

    @staticmethod
    def _stratified_sample(
        entries: List[Dict],
        key_fn,
        n: int,
        rng: random.Random,
    ) -> List[Dict]:
        if not entries or n <= 0:
            return []
        groups: Dict[str, List[Dict]] = {}
        for entry in entries:
            groups.setdefault(str(key_fn(entry)), []).append(entry)
        per_type = max(1, n // len(groups))
        selected: List[Dict] = []
        group_items_list = list(groups.values())
        if len(group_items_list) > n:
            group_items_list = rng.sample(group_items_list, n)
        for group_items in group_items_list:
            selected.extend(rng.sample(group_items, min(per_type, len(group_items))))
        remaining = n - len(selected)
        if remaining > 0:
            selected_ids = {id(entry) for entry in selected}
            pool = [entry for entry in entries if id(entry) not in selected_ids]
            if pool:
                selected.extend(rng.sample(pool, min(remaining, len(pool))))
        return selected

    def _build_probe_set(
        self,
        *,
        all_entries: List[Dict],
        prev_results: Optional[Dict[str, bool]],
        epoch: int,
        update_cycle: int,
        rng: random.Random,
    ) -> Tuple[List[Dict], set]:
        half = self.grpo_eval_n // 2
        type_key = lambda e: e.get("query_type") or e.get("_sample", {}).get("template") or "other"

        prior_entries = [
            e for e in all_entries
            if e.get("update_cycle", update_cycle) < update_cycle
        ]
        if prior_entries:
            failing = [e for e in prior_entries if not e.get("is_correct")]
            passing = [e for e in prior_entries if e.get("is_correct")]
            probe_failing_ids = {str(e["sample_id"]) for e in failing}
            probe = (
                self._stratified_sample(failing, type_key, half, rng)
                + self._stratified_sample(passing, type_key, half, rng)
            )
            return probe, probe_failing_ids

        if epoch > 0 and prev_results:
            id_to_sample = {str(s["question_id"]): s for s in self.dev_data}
            prev_entries = []
            for sid, ok in prev_results.items():
                sample = id_to_sample.get(str(sid))
                if sample is None:
                    continue
                prev_entries.append({
                    "sample_id": str(sid),
                    "query_type": sample.get("template") or sample.get("main_table_name"),
                    "is_correct": bool(ok),
                    "update_cycle": update_cycle - 1,
                    "_sample": sample,
                })
            failing = [e for e in prev_entries if not e.get("is_correct")]
            passing = [e for e in prev_entries if e.get("is_correct")]
            probe_failing_ids = {str(e["sample_id"]) for e in failing}
            probe = (
                self._stratified_sample(failing, type_key, half, rng)
                + self._stratified_sample(passing, type_key, half, rng)
            )
            return probe, probe_failing_ids

        if all_entries:
            failing = [e for e in all_entries if not e.get("is_correct")]
            passing = [e for e in all_entries if e.get("is_correct")]
            probe_failing_ids = {str(e["sample_id"]) for e in failing}
            probe = (
                self._stratified_sample(failing, type_key, half, rng)
                + self._stratified_sample(passing, type_key, half, rng)
            )
            return probe, probe_failing_ids

        return [], set()

    def _evaluate_split(self, samples: List[Dict], path: Path, update_cycle: int) -> float:
        print(f"[Eval] evaluating {len(samples)} samples -> {path}")
        entries = self._run_samples(
            samples,
            self.skill_repo,
            update_cycle=update_cycle,
            append_path=path,
        )
        if not entries:
            return 0.0
        return sum(e["is_correct"] for e in entries) / len(entries)

    def _run_samples(
        self,
        samples: List[Dict],
        repo: SkillRepository,
        update_cycle: int,
        append_path: Optional[Path] = None,
    ) -> List[Dict]:
        sample_by_id = {str(sample.get("question_id")): sample for sample in samples}
        results: List[Dict] = []
        completed_ids = set()
        if append_path:
            append_path.parent.mkdir(parents=True, exist_ok=True)
            if self.resume and append_path.exists():
                for entry in self._read_jsonl(append_path):
                    sid = str(entry.get("sample_id"))
                    if sid not in sample_by_id or sid in completed_ids:
                        continue
                    entry["_sample"] = sample_by_id[sid]
                    results.append(entry)
                    completed_ids.add(sid)
                if completed_ids:
                    print(
                        f"[Resume] loaded {len(completed_ids)}/{len(samples)} "
                        f"completed samples from {append_path}",
                        flush=True,
                    )
            else:
                append_path.touch(exist_ok=True)
        pending_samples = [
            sample
            for sample in samples
            if str(sample.get("question_id")) not in completed_ids
        ]
        print(
            f"[RunSamples] starting {len(pending_samples)} pending / {len(samples)} total "
            f"(update_cycle={update_cycle})",
            flush=True,
        )
        self._write_state(
            "run_samples",
            update_cycle=update_cycle,
            total=len(samples),
            completed=len(results),
            append_path=str(append_path) if append_path else None,
        )
        with ThreadPoolExecutor(max_workers=self.batch_concurrency) as executor:
            futures = {
                executor.submit(self._run_one, sample, repo, update_cycle): sample
                for sample in pending_samples
            }
            for future in self._progress(as_completed(futures), total=len(futures), desc="FHIR samples"):
                sample = futures[future]
                try:
                    entry = future.result()
                except BaseException as e:
                    error_trace = "".join(
                        traceback.format_exception(type(e), e, e.__traceback__)
                    )
                    print(
                        f"[FHIRSkillCycle] sample runner failed for "
                        f"{sample.get('question_id')}: {type(e).__name__}: {e}\n"
                        f"{error_trace}",
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
                        "traceback": error_trace,
                        "ground_truth": sample.get("true_answer"),
                        "task_result": {},
                        "agent_actions": [],
                        "history": [],
                        "failure_tags": [
                            str(x)
                            for x in [sample.get("template"), sample.get("main_table_name")]
                            if x
                        ],
                        "skill_snapshot_before": repo.snapshot(),
                        "_sample": sample,
                    }
                results.append(entry)
                if append_path:
                    with open(append_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(self._json_safe(entry), default=str) + "\n")
                self._write_state(
                    "run_samples",
                    update_cycle=update_cycle,
                    total=len(samples),
                    completed=len(results),
                    correct=sum(bool(e.get("is_correct")) for e in results),
                    append_path=str(append_path) if append_path else None,
                )
        results.sort(key=lambda e: str(e["sample_id"]))
        print(
            f"[RunSamples] finished {len(results)} samples "
            f"score={sum(bool(e.get('is_correct')) for e in results)}/{len(results)}",
            flush=True,
        )
        self._write_state(
            "run_samples_finished",
            update_cycle=update_cycle,
            total=len(samples),
            completed=len(results),
            correct=sum(bool(e.get("is_correct")) for e in results),
            append_path=str(append_path) if append_path else None,
        )
        return results

    def _run_one(self, sample: Dict, repo: SkillRepository, update_cycle: int) -> Dict:
        import tools.cache as cache_module

        cache_module.CACHE_ENABLED = bool(self.config.get("agent", {}).get("enable_cache", True))
        agent = create_skill_aware_fhir_agent(
            agent_strategy=self.agent_strategy,
            model=self.agent_model,
            base_url=self.agent_base_url,
            verbose=self.verbose_agent,
            skill_repo=repo,
            timeout=self.agent_timeout,
            max_retries=self.agent_max_retries,
            max_tokens=self.agent_max_tokens,
        )
        try:
            if self.agent_sample_timeout:
                with ThreadPoolExecutor(max_workers=1) as _pool:
                    _future = _pool.submit(agent.run, sample["question_with_context"])
                    try:
                        raw_output = _future.result(timeout=self.agent_sample_timeout)
                    except TimeoutError:
                        _future.cancel()
                        raise TimeoutError(f"sample wall-clock timeout ({self.agent_sample_timeout}s)")
            else:
                raw_output = agent.run(sample["question_with_context"])
            parsed = parse_outputs(raw_output)
        except Exception as e:
            raw_output = {"error": str(e), "trace": []}
            parsed = {"agent_answer": None, "agent_fhir_resources": None, "trace": [], "usage": None, "error": str(e)}

        trace = [serialize_message(m) for m in (parsed.get("trace") or raw_output.get("trace") or []) if m is not None]
        is_correct = self.evaluator.score(sample, parsed)
        return {
            "sample_id": sample["question_id"],
            "instruction": sample["question"],
            "query_type": sample.get("template") or sample.get("main_table_name"),
            "is_correct": is_correct,
            "update_cycle": update_cycle,
            "status": "completed" if not parsed.get("error") else (
                "sample_timeout" if "sample wall-clock timeout" in (parsed.get("error") or "") else "agent_error"
            ),
            "error": parsed.get("error"),
            "ground_truth": sample.get("true_answer"),
            "task_result": {
                "reported_answer": parsed.get("agent_answer"),
                "retrieved_fhir_resources": parsed.get("agent_fhir_resources"),
                "usage": parsed.get("usage"),
            },
            "agent_actions": format_agent_actions(trace),
            "history": trace,
            "failure_tags": [str(x) for x in [sample.get("template"), sample.get("main_table_name")] if x],
            "skill_snapshot_before": repo.snapshot(),
            "_sample": sample,
        }

    @staticmethod
    def _json_safe(entry: Dict) -> Dict:
        return {k: v for k, v in entry.items() if not k.startswith("_")}

    @staticmethod
    def _read_jsonl(path: Path) -> List[Dict]:
        entries: List[Dict] = []
        if not path.exists():
            return entries
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    def _write_jsonl(self, path: Path, entries: List[Dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(self._json_safe(entry), default=str) + "\n")

    def _append_jsonl(self, path: Path, entries: List[Dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(self._json_safe(entry), default=str) + "\n")


def _apply_overrides(config: dict, overrides) -> None:
    for item in overrides or []:
        if "=" not in item:
            print(f"Invalid --set value (expected key=value): {item}", file=sys.stderr)
            sys.exit(1)
        key, _, raw = item.partition("=")
        keys = key.split(".")
        node = config
        for k in keys[:-1]:
            if k not in node or not isinstance(node[k], dict):
                node[k] = {}
            node = node[k]
        node[keys[-1]] = yaml.safe_load(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill-learning cycle for FHIR-AgentBench")
    parser.add_argument("--config", "-c", default="configs/grasp.yaml")
    parser.add_argument("--run-name", "-n", default=None)
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--resume", "-r", action="store_true")
    parser.add_argument("--set", metavar="KEY=VALUE", nargs="*", default=[])
    parser.add_argument("--agent", "-a", default=None, metavar="PRESET",
                        help="Backend preset (configs/agents/<PRESET>.yaml); overrides GRASP_BACKEND and agent_preset.")
    args = parser.parse_args()

    config_path = Path(args.config)
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    _apply_overrides(config, args.set)
    apply_backend(config, args.agent)

    run_name = args.run_name or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(config.get("output_dir", "outputs/grasp")) / run_name
    if args.force and args.resume:
        raise SystemExit("--force and --resume are mutually exclusive.")
    if run_dir.exists() and args.force:
        shutil.rmtree(run_dir)
    elif run_dir.exists() and not args.resume:
        raise SystemExit(f"Run directory already exists: {run_dir}. Use --force to overwrite.")
    run_dir.mkdir(parents=True, exist_ok=True)
    config["_resume"] = bool(args.resume)
    if args.resume and (run_dir / "config.yaml").exists():
        print(f"Resuming run directory: {run_dir}")
    else:
        (run_dir / "config.yaml").write_text(yaml.dump(config), encoding="utf-8")
    print(f"Run directory: {run_dir}")

    runner = FHIRSkillCycleRunner(config, run_dir)
    runner.run()
    runner.run_test_eval()
    runner.run_baseline_test_eval()


if __name__ == "__main__":
    main()
