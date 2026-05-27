"""Evaluation function for WebShop tasks.

The WebShop env returns a per-episode ``reward`` in [0, 1] (1.0 = the purchased
product matched every attribute/option/price requirement of the instruction).
AgentBench reports mean reward as the headline metric and "success rate" as the
fraction of episodes with reward == 1.0. The skill cycle needs a binary signal,
so we treat an episode as correct only when it earns full reward — the standard
WebShop success-rate definition.

Relax ``SUCCESS_THRESHOLD`` (e.g. to 0.75) if you want partial-match credit to
count as a positive learning signal.
"""

from src.typings import TaskOutput

SUCCESS_THRESHOLD = 1.0


def eval(sample: dict, task_output: TaskOutput) -> bool:
    """Return True if the episode earned full WebShop reward."""
    if task_output is None or task_output.result is None:
        return False
    try:
        return float(task_output.result.get("reward", 0)) >= SUCCESS_THRESHOLD
    except (AttributeError, TypeError, ValueError):
        return False
