from .http_agent import HTTPAgent
from .skill_aware_agent import SkillAwareAgent
from .vertex_agent import VertexAgent

try:
    from .fastchat_client import FastChatAgent
except ImportError:
    FastChatAgent = None

__all__ = [
    "HTTPAgent",
    "SkillAwareAgent",
    "VertexAgent",
    "FastChatAgent",
]


def __getattr__(name):
    if name == "LiteLLMAgent":
        from .litellm_agent import LiteLLMAgent

        return LiteLLMAgent
    if name == "OpenAIResponsesAgent":
        from .openai_responses_agent import OpenAIResponsesAgent

        return OpenAIResponsesAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
