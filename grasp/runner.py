"""
High-level entry point: load a config, build a run, and execute a method.

``run_grasp`` is the one-call path used by examples and CLIs — give it a
:class:`~grasp.task.Task` and a config file, and it resolves the backend,
prepares the run directory, and runs GRASP end to end.

``run_method`` is the generic form for any :class:`~grasp.method.Method`
subclass (e.g. when benchmarking your own self-improvement method).
"""

from pathlib import Path
from typing import Iterable, Optional, Type

from .config import prepare_run
from .cycle import SkillLearningMethod
from .method import Method
from .task import Task


def run_method(
    method_cls: Type[Method],
    task: Task,
    config_path,
    *,
    overrides: Optional[Iterable[str]] = None,
    agent: Optional[str] = None,
    run_name: Optional[str] = None,
    force: bool = False,
    resume: bool = False,
    agents_dir=None,
) -> Path:
    """Prepare a run from ``config_path`` and execute ``method_cls`` on ``task``.

    Returns the run directory. ``agent`` selects a backend preset (overriding
    ``GRASP_BACKEND`` and the config's ``agent_preset``).
    """
    config, run_dir = prepare_run(
        config_path,
        overrides=overrides,
        cli_agent=agent,
        run_name=run_name,
        force=force,
        resume=resume,
        agents_dir=agents_dir,
    )
    method = method_cls(config, run_dir, task)
    method.run()
    return run_dir


def run_grasp(task: Task, config_path, **kwargs) -> Path:
    """Run the reference GRASP method on ``task``. See :func:`run_method`."""
    return run_method(SkillLearningMethod, task, config_path, **kwargs)
