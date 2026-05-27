"""
The ``Task`` interface — how a benchmark plugs into GRASP.

A GRASP run needs three things from a benchmark: a set of samples (split into
dev / val / test), a way to run an agent on one sample, and a way to score the
result. ``Task`` is that contract. Implement it once for your environment and
any ``Method`` in this package can learn on it; see ``docs/add_a_task.md``.

The paper benchmarks under ``benchmarks/`` predate this interface and drive the
agent through their own client/server harness — ``Task`` is the small,
in-process surface the reusable core is built against.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Rollout:
    """The result of running an agent on one sample.

    The skill-learning loop reads these fields when logging runs and when
    summarizing failures for the skill writer:

    - ``history``: full chat-style transcript (list of ``{"role", "content"}``).
    - ``agent_actions``: the agent's actions/tool calls as readable strings,
      used to describe failure traces to the skill writer.
    - ``answer``: the agent's final answer text, if the task has one.
    - ``status``: ``"completed"`` normally, or a short status such as
      ``"agent invalid action"`` / ``"agent context limit"`` that the loop may
      treat specially.
    - ``raw``: the untouched native output, for task-specific evaluation.
    """

    history: List[Dict[str, Any]] = field(default_factory=list)
    agent_actions: List[str] = field(default_factory=list)
    answer: str = ""
    status: str = "completed"
    raw: Any = None


class Task(ABC):
    """A benchmark GRASP can learn on.

    Implementations are expected to be safe to call concurrently across samples
    (the loop runs a batch in parallel threads); keep per-call state local.
    """

    #: Human-readable name, used in logs and run summaries.
    name: str = "task"

    @abstractmethod
    def samples(self, split: str) -> List[Dict[str, Any]]:
        """Return the samples for ``split`` (one of ``"dev"``, ``"val"``, ``"test"``).

        Each sample is a dict; the only required key is a stable identifier
        under ``"id"``. All other keys are task-specific and passed straight
        back to :meth:`rollout` and :meth:`evaluate`.
        """

    @abstractmethod
    def rollout(self, sample: Dict[str, Any], agent: Any) -> Rollout:
        """Run ``agent`` on ``sample`` for one episode and return a :class:`Rollout`.

        ``agent`` exposes ``inference(history, tools=None) -> response`` (the
        GRASP agent contract). During learning the agent is wrapped so the
        current skill library is injected before each inference call; this
        method does not need to know about skills.
        """

    @abstractmethod
    def evaluate(self, sample: Dict[str, Any], rollout: Rollout) -> bool:
        """Return ``True`` iff the rollout solved the sample."""

    def failure_tags(self, sample: Dict[str, Any], rollout: Rollout) -> List[str]:
        """Optional: short tags describing *why* a sample failed.

        Returned tags are surfaced to the skill writer to group failures by
        mechanism. Default: no tags. Override to improve proposal quality on
        benchmarks with characteristic failure modes.
        """
        return []
