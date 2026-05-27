"""Evaluation function for ALFWorld tasks."""

from src.typings import TaskOutput


def eval(sample: dict, task_output: TaskOutput) -> bool:
    """Return True if ALFWorld reports the game was completed successfully."""
    if task_output is None or task_output.result is None:
        return False
    try:
        return bool(task_output.result.get("result", 0))
    except (AttributeError, TypeError):
        return False
