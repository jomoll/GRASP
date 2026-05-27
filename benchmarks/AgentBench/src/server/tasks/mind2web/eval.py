"""
Evaluation function for Mind2Web (Web Browsing) tasks.

Returns True if the agent correctly identified the target DOM element.
Element accuracy is the primary skill-cycle signal; step_sr (element +
perfect action F1) is also stored in the result for reference but is too
strict to use as a learning signal when the model omits Action/Value lines.
"""

from src.typings import TaskOutput


def eval(sample: dict, task_output: TaskOutput) -> bool:
    """
    Args:
        sample: Split-file dict with key "id" (integer sample index).
        task_output: TaskOutput returned by the task worker.

    Returns:
        True if the agent selected the correct DOM element.
    """
    if task_output is None or task_output.result is None:
        return False
    return bool(task_output.result.get("element_correct", False))
