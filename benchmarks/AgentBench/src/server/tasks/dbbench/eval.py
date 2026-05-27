"""
Evaluation function for DBBench tasks.

Returns True if the agent's answer matches the ground truth.

Ground truth is stored in the split file under "answer":
  - SELECT-type queries: list of expected string values (the "label" field)
  - INSERT/UPDATE/DELETE: MD5 hash string (the "answer_md5" field)

For mutation queries, the task stores the scored DB-state hash in
task_output.result["answer"].
For SELECT-style queries, the primary answer is task_output.result["answer"] and
we fall back to task_output.result["reported_answer"] if needed. This keeps the
benchmark robust when the task worker and training loop inspect different answer
fields while preserving the same semantics.
"""

import ast

from src.typings import TaskOutput


def _matches_select_answer(agent_answer, ground_truth) -> bool:
    try:
        parsed = list(ast.literal_eval(str(agent_answer)))
    except Exception:
        parsed = [str(agent_answer)]

    cor = ground_truth if isinstance(ground_truth, list) else [ground_truth]

    if len(parsed) == 1 and len(cor) == 1:
        try:
            return float(str(parsed[0]).replace(',', '')) == float(str(cor[0]).replace(',', ''))
        except (ValueError, TypeError):
            return str(parsed[0]).strip() == str(cor[0]).strip()

    try:
        return set(str(x).strip() for x in parsed) == set(str(x).strip() for x in cor)
    except Exception:
        return False


def eval(sample: dict, task_output: TaskOutput) -> bool:
    """
    Args:
        sample: Split-file dict with keys "id", "description", "type", "answer".
        task_output: TaskOutput returned by the task worker.

    Returns:
        True if the agent solved the task correctly.
    """
    if task_output is None or task_output.result is None:
        return False

    result = task_output.result
    agent_answer = result.get("answer", "")
    reported_answer = result.get("reported_answer", "")
    query_type = sample.get("type", result.get("type", "other"))
    ground_truth = sample.get("answer")

    if ground_truth is None:
        return False

    # Mutation queries: MD5 hash string comparison
    if query_type in ("INSERT", "DELETE", "UPDATE"):
        return str(agent_answer).strip() == str(ground_truth).strip()

    # SELECT-type queries: compare the stored answer, then the reported final answer.
    if _matches_select_answer(agent_answer, ground_truth):
        return True
    if reported_answer and str(reported_answer).strip() != str(agent_answer).strip():
        return _matches_select_answer(reported_answer, ground_truth)
    return False
