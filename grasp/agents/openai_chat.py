"""
OpenAIChatAgent — a minimal OpenAI-compatible chat agent with no third-party
dependencies (uses the standard library ``urllib``).

It targets any endpoint exposing ``POST {base_url}/chat/completions`` — OpenAI,
a self-hosted vLLM/llama.cpp server, LiteLLM proxy, etc. This is the agent
behind the ``local`` backend preset used by the quickstart.

The GRASP loop records agent turns with role ``"agent"``; this client maps that
to ``"assistant"`` on the wire so any chat model understands the transcript.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ..agent import AgentClient

_ROLE_MAP = {"agent": "assistant"}


class OpenAIChatAgent(AgentClient):
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "EMPTY",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 120.0,
        **extra: Any,
    ) -> None:
        super().__init__()
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.extra = extra  # passed through into the request body

    def _messages(self, history: List[dict]) -> List[Dict[str, str]]:
        out = []
        for m in history:
            role = m.get("role", "user")
            out.append({"role": _ROLE_MAP.get(role, role),
                        "content": str(m.get("content", "") or "")})
        return out

    def inference(self, history: List[dict], tools=None) -> str:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": self._messages(history),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        body.update(self.extra)
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"] or ""
