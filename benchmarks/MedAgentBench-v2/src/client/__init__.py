from .agent import AgentClient
from .task import TaskClient

_AGENT_EXPORTS = {
    "FastChatAgent",
    "HTTPAgent",
    "LiteLLMAgent",
    "VertexAgent",
    "SkillAwareAgent",
    "PostVerifyingAgent",
}

__all__ = [
    "AgentClient",
    "TaskClient",
    "FastChatAgent",
    "HTTPAgent",
    "VertexAgent",
    "SkillAwareAgent",
    "PostVerifyingAgent",
]


def __getattr__(name):
    if name in _AGENT_EXPORTS:
        from . import agents

        return getattr(agents, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
