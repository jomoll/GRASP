import time
from typing import List, Optional

import litellm
litellm.drop_params = True
litellm.suppress_debug_info = True

from ..agent import AgentClient, AgentContextLimitException


class LiteLLMAgent(AgentClient):
    """
    Agent client backed by LiteLLM, supporting any provider it covers
    (OpenAI, Anthropic, Gemini via API key, Mistral, local via base_url, …).

    Usage in config:
        module: src.client.agents.LiteLLMAgent
        parameters:
            model: "gpt-4o-mini"          # or "claude-3-5-haiku-...", etc.
            api_key: "sk-..."             # optional; falls back to env var
            base_url: "http://..."        # optional; for local / proxy endpoints
            temperature: 0.0
            max_output_tokens: 32768
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        api_version: Optional[str] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 32768,
        max_retries: int = 3,
        timeout: int = 120,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.api_version = api_version
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.max_retries = max_retries
        self.timeout = timeout

    def _to_openai_messages(self, history: List[dict]) -> List[dict]:
        role_map = {"user": "user", "agent": "assistant"}
        return [{"role": role_map.get(m["role"], m["role"]), "content": m["content"]} for m in history]

    def inference(self, history: List[dict]) -> str:
        messages = self._to_openai_messages(history)
        base_delay = 5

        for attempt in range(self.max_retries):
            try:
                resp = litellm.completion(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_output_tokens,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    api_version=self.api_version,
                    timeout=self.timeout,
                )
                return resp.choices[0].message.content

            except litellm.ContextWindowExceededError as e:
                raise AgentContextLimitException(str(e))

            except litellm.RateLimitError:
                delay = min(base_delay * (2 ** attempt), 60)
                print(f"Rate limited (attempt {attempt + 1}/{self.max_retries}), waiting {delay}s...")
                time.sleep(delay)

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                print(f"Warning (attempt {attempt + 1}): {e}")
                time.sleep(base_delay * (attempt + 1))

        raise Exception(f"Failed after {self.max_retries} attempts")
