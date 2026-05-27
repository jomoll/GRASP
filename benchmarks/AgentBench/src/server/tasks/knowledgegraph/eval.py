"""Evaluation function for Knowledge Graph (Freebase) tasks.

The KnowledgeGraph task reports correctness in ``result`` as ``is_correct`` —
True only when the agent's submitted answer set exactly matches the gold answer
set (full intersection, no extras), matching the upstream AgentBench KG metric.
``result`` also carries the F1 score and the predicted/gold answer sets for
debugging. The skill cycle reads ``is_correct`` directly when present, so this
function is the path used by ``eval_test.py`` and any caller that does not.
"""

from src.typings import TaskOutput


def eval(sample: dict, task_output: TaskOutput) -> bool:
    """Return True if the agent's answer set exactly matched the gold answer set."""
    if task_output is None or task_output.result is None:
        return False
    try:
        return task_output.result.get("is_correct") is True
    except (AttributeError, TypeError):
        return False
