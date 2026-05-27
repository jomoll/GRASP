"""
Evaluation function for Card Game tasks.

Returns True if the agent won the game.
The CardGame task stores per-game metrics in result["meta"], where each entry
has a "win_round" key (1 = agent won, 0 = agent lost).
"""

from src.typings import TaskOutput


def eval(sample: dict, task_output: TaskOutput) -> bool:
    """
    Args:
        sample: Split-file dict with keys "id", "stage", "baseline", "agent".
        task_output: TaskOutput returned by the task worker.

    Returns:
        True if the agent won the game.
    """
    if task_output is None or task_output.result is None:
        return False
    try:
        meta = task_output.result.get("meta", {})
        if not meta:
            return False
        val = next(iter(meta.values()))
        return bool(val.get("win_round", 0))
    except (AttributeError, TypeError):
        return False
