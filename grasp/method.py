"""
The ``Method`` interface — how a self-improvement method plugs into GRASP.

A method is given a config, a run directory to write into, and a :class:`Task`
to learn on. Its job is to implement ``run()``: the learning loop that improves
the agent over the task's dev split and monitors the val split. GRASP itself is
the reference implementation (:class:`grasp.SkillLearningMethod`, added in
``grasp/cycle.py``); the five paper baselines are worked examples to diff
against (see ``docs/add_a_method.md``).

This base class deliberately just formalizes the convention the paper's
``*CycleRunner`` classes already follow — ``__init__(config, run_dir, …)`` plus
``run()`` — so existing methods need no rewrite to be understood through it.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

from .task import Task


class Method(ABC):
    """Base class for a self-improvement method.

    Subclasses implement :meth:`run`. The harness constructs the method with the
    resolved config, a fresh (or resumed) run directory, and the task to learn
    on, then calls :meth:`run` once.
    """

    def __init__(self, config: Dict[str, Any], run_dir: Path, task: Task) -> None:
        self.config = config
        self.run_dir = Path(run_dir)
        self.task = task

    @abstractmethod
    def run(self) -> None:
        """Execute the method end to end, writing artifacts into ``self.run_dir``.

        Conventional outputs (not enforced) include per-epoch logs, the learned
        skill/memory library, and a ``val_scores.json`` learning curve, so runs
        from different methods can be compared with the same tooling.
        """
