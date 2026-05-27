"""
Evaluation function for Lateral Thinking Puzzle (LTP) tasks.

Returns True if the agent successfully solved the puzzle (discovered all answer-key
clues within the round limit). The LTP task stores the outcome in result["finished"].

Secondary metric: result["progress"] = fraction of answer-key points discovered
(used by calculate_overall but not by the binary skill-cycle eval).
"""

from src.typings import TaskOutput


def eval(sample: dict, task_output: TaskOutput) -> bool:
    """
    Args:
        sample: Split-file dict with keys "id", "story", "answer", etc.
        task_output: TaskOutput returned by the task worker.

    Returns:
        True if the agent solved the puzzle (finished=True).
    """
    if task_output is None or task_output.result is None:
        return False
    try:
        return bool(task_output.result.get("finished", False))
    except (AttributeError, TypeError):
        return False
