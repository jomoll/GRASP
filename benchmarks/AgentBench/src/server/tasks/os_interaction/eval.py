"""Evaluation function for OS Interaction tasks."""

from src.typings import TaskOutput


def eval(sample: dict, task_output: TaskOutput) -> bool:
    """Return True when the task worker judged the OS sample correct."""
    if task_output is None or task_output.result is None:
        return False
    try:
        return bool(task_output.result.get("result", False))
    except (AttributeError, TypeError):
        return False
