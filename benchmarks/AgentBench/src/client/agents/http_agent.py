import contextlib
import random
import re
import time
import warnings
from datetime import datetime as DateTime, timezone

import requests
from urllib3.exceptions import InsecureRequestWarning

from src.typings import *
from src.utils import *
from ..agent import AgentClient

old_merge_environment_settings = requests.Session.merge_environment_settings


@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except:
                pass


class Prompter:
    @staticmethod
    def get_prompter(prompter: Union[Dict[str, Any], None]):
        # check if prompter_name is a method and its variable
        if not prompter:
            return Prompter.default()
        assert isinstance(prompter, dict)
        prompter_name = prompter.get("name", None)
        prompter_args = prompter.get("args", {})
        if hasattr(Prompter, prompter_name) and callable(
            getattr(Prompter, prompter_name)
        ):
            return getattr(Prompter, prompter_name)(**prompter_args)
        return Prompter.default()

    @staticmethod
    def default():
        return Prompter.role_content_dict()

    @staticmethod
    def batched_role_content_dict(*args, **kwargs):
        base = Prompter.role_content_dict(*args, **kwargs)

        def batched(messages):
            result = base(messages)
            return {key: [result[key]] for key in result}

        return batched

    @staticmethod
    def role_content_dict(
        message_key: str = "messages",
        role_key: str = "role",
        content_key: str = "content",
        user_role: str = "user",
        agent_role: str = "agent",
    ):
        def prompter(messages: List[Dict[str, str]]):
            nonlocal message_key, role_key, content_key, user_role, agent_role
            role_dict = {
                "user": user_role,
                "agent": agent_role,
                "assistant": agent_role,
                "system": "system",
                "tool": "tool",
            }
            prompt = []
            for item in messages:
                message = dict(item)
                message[role_key] = role_dict.get(item["role"], item["role"])
                if content_key != "content" and "content" in message:
                    message[content_key] = message.pop("content")
                if role_key != "role":
                    message.pop("role", None)
                prompt.append(message)
            return {message_key: prompt}

        return prompter

    @staticmethod
    def prompt_string(
        prefix: str = "",
        suffix: str = "AGENT:",
        user_format: str = "USER: {content}\n\n",
        agent_format: str = "AGENT: {content}\n\n",
        prompt_key: str = "prompt",
    ):
        def prompter(messages: List[Dict[str, str]]):
            nonlocal prefix, suffix, user_format, agent_format, prompt_key
            prompt = prefix
            for item in messages:
                if item["role"] == "user":
                    prompt += user_format.format(content=item["content"])
                else:
                    prompt += agent_format.format(content=item["content"])
            prompt += suffix
            print(prompt)
            return {prompt_key: prompt}

        return prompter

    @staticmethod
    def claude():
        return Prompter.prompt_string(
            prefix="",
            suffix="Assistant:",
            user_format="Human: {content}\n\n",
            agent_format="Assistant: {content}\n\n",
        )

    @staticmethod
    def palm():
        def prompter(messages):
            return {"instances": [
                Prompter.role_content_dict("messages", "author", "content", "user", "bot")(messages)
            ]}
        return prompter


def _parse_retry_delay(response_text: str, attempt: int, base_delay: float, max_delay: float) -> float:
    m = re.search(r"Limit resets at:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UTC", response_text)
    if m:
        try:
            reset_dt = DateTime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            wait = (reset_dt - DateTime.now(timezone.utc)).total_seconds()
            return max(1.0, min(wait + 2.0, max_delay))
        except ValueError:
            pass
    m = re.search(r"[Tt]ry again in (\d+(?:\.\d+)?)\s*second", response_text)
    if m:
        return min(float(m.group(1)) + 1.0, max_delay)
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = delay * 0.2 * (random.random() - 0.5)
    return max(1.0, delay + jitter)


def check_context_limit(content: str):
    content = content.lower()
    and_words = [
        ["prompt", "context", "tokens"],
        [
            "limit",
            "exceed",
            "max",
            "long",
            "much",
            "many",
            "reach",
            "over",
            "up",
            "beyond",
        ],
    ]
    rule = AndRule(
        [
            OrRule([ContainRule(word) for word in and_words[i]])
            for i in range(len(and_words))
        ]
    )
    return rule.check(content)


class HTTPAgent(AgentClient):
    def __init__(
        self,
        url,
        proxies=None,
        body=None,
        headers=None,
        return_format="{response}",
        prompter=None,
        max_retries: int = 10,
        retry_base_delay: float = 5.0,
        retry_max_delay: float = 60.0,
        timeout: int = 120,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url
        self.proxies = proxies or {}
        self.headers = headers or {}
        self.body = body or {}
        self.return_format = return_format
        self.prompter = Prompter.get_prompter(prompter)
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        self.timeout = timeout
        if not self.url:
            raise Exception("Please set 'url' parameter")

    def _handle_history(self, history: List[dict]) -> Dict[str, Any]:
        return self.prompter(history)

    def inference(self, history: List[dict], tools: Union[List[Dict[str, Any]], None] = None):
        for attempt in range(self.max_retries):
            try:
                body = self.body.copy()
                body.update(self._handle_history(history))
                if tools is not None:
                    body["tools"] = tools
                else:
                    body.pop("tool_choice", None)
                    body.pop("parallel_tool_calls", None)
                with no_ssl_verification():
                    resp = requests.post(
                        self.url, json=body, headers=self.headers, proxies=self.proxies, timeout=self.timeout
                    )
                if resp.status_code == 429:
                    wait = _parse_retry_delay(resp.text, attempt, self.retry_base_delay, self.retry_max_delay)
                    print(f"Warning:  Rate limited (attempt {attempt + 1}/{self.max_retries}), retrying in {wait:.1f}s")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    if check_context_limit(resp.text):
                        raise AgentContextLimitException(resp.text)
                    raise Exception(f"Invalid status code {resp.status_code}:\n\n{resp.text}")
            except AgentClientException as e:
                raise e
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait = _parse_retry_delay(str(e), attempt, self.retry_base_delay, self.retry_max_delay)
                print(f"Warning:  {e}")
                time.sleep(wait)
                continue

            resp = resp.json()
            if isinstance(resp, dict) and resp.get("choices"):
                message = resp["choices"][0].get("message", {})
                if message.get("tool_calls"):
                    return message
                if "content" in message:
                    return message.get("content") or ""
            return self.return_format.format(response=resp)
        raise Exception("Failed.")
