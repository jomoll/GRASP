"""GRASP — self-improvement via a regression-gated skill library.

GRASP learns a small library of reusable skills from an agent's own failure
traces, accepting a proposed skill edit only when it improves performance on a
held-out probe set (the regression gate).

This package is the reusable core. See the top-level README for the quickstart
and ``docs/`` for the method, the ``Method`` interface for plugging in your own
self-improvement method, and ``Task`` for plugging in your own benchmark.

The full paper benchmarks live under ``benchmarks/`` and the released results
under ``results/``.
"""

__version__ = "0.1.0"

from .task import Task, Rollout
from .method import Method
from .skills import SkillRepository
from .cycle import SkillLearningMethod, SkillCycleRunner
from .runner import run_grasp, run_method

__all__ = [
    "Task",
    "Rollout",
    "Method",
    "SkillRepository",
    "SkillLearningMethod",
    "SkillCycleRunner",
    "run_grasp",
    "run_method",
    "__version__",
]
