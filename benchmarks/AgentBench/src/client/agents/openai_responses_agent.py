import os
import time
from typing import List, Optional

from openai import OpenAI, BadRequestError, RateLimitError

from ..agent import AgentClient

try:
    from src.typings import AgentContextLimitException
except Exception:  # pragma: no cover - fallback if typings layout differs
    class AgentContextLimitException(Exception):
        pass


class OpenAIResponsesAgent(AgentClient):
    """
    Agent client using the OpenAI Responses API for GPT-5 series models on Azure.

    Usage in config:
        module: src.client.agents.OpenAIResponsesAgent
        parameters:
            model: "gpt-5.4-mini"
            base_url: "https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/"
            reasoning_effort: "low"    # low, medium, or high
            text_verbosity: "low"      # GPT-5 series only
            max_output_tokens: 32768
            timeout: 300
    """

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        reasoning_effort: Optional[str] = "low",
        text_verbosity: Optional[str] = "low",
        max_output_tokens: int = 32768,
        max_retries: int = 3,
        timeout: int = 300,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.text_verbosity = text_verbosity
        self.max_output_tokens = max_output_tokens
        self.max_retries = max_retries
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"),
            timeout=timeout,
            max_retries=0,
        )

    def _to_responses_input(self, history: List[dict]) -> List[dict]:
        role_map = {"user": "user", "agent": "assistant", "system": "developer"}
        return [{"role": role_map.get(m["role"], m["role"]), "content": m["content"]} for m in history]

    def inference(self, history: List[dict]) -> str:
        messages = self._to_responses_input(history)
        base_delay = 5

        call_kwargs = {
            "model": self.model,
            "input": messages,
            "max_output_tokens": self.max_output_tokens,
        }
        if self.reasoning_effort:
            call_kwargs["reasoning"] = {"effort": self.reasoning_effort, "summary": "auto"}
        if self.text_verbosity:
            call_kwargs["text"] = {"verbosity": self.text_verbosity}

        for attempt in range(self.max_retries):
            try:
                resp = self.client.responses.create(**call_kwargs)
                return resp.output_text

            except BadRequestError as e:
                if "context" in str(e).lower():
                    raise AgentContextLimitException(str(e))
                if attempt == self.max_retries - 1:
                    raise
                print(f"Warning (attempt {attempt + 1}): {e}")
                time.sleep(base_delay * (attempt + 1))

            except RateLimitError:
                delay = min(base_delay * (2 ** attempt), 60)
                print(f"Rate limited (attempt {attempt + 1}/{self.max_retries}), waiting {delay}s...")
                time.sleep(delay)

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                print(f"Warning (attempt {attempt + 1}): {e}")
                time.sleep(base_delay * (attempt + 1))

        raise Exception(f"Failed after {self.max_retries} attempts")
