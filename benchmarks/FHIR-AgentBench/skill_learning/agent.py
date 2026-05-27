import copy
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from core_utils import create_agent, safe_llm_call

from .repository import SkillRepository


def render_skills(skill_repo: SkillRepository) -> str:
    skills = [s for s in skill_repo.load_all() if s["name"] != "skeleton"]
    if not skills:
        return ""
    blocks = [
        "Behavioral skills: before each tool call or final answer, scan these "
        "rules. Use a skill only when its trigger matches the current FHIR "
        "question, retrieved resources, or answer-format requirement."
    ]
    for skill in skills:
        desc = skill.get("description", "")
        desc_line = f"When to use: {desc}\n" if desc else ""
        blocks.append(f"### {skill['name']}\n{desc_line}{skill.get('content', '')}")
    return "\n\n".join(blocks)


def create_skill_aware_fhir_agent(
    *,
    agent_strategy: str,
    model: str,
    base_url: Optional[str],
    verbose: bool,
    skill_repo: SkillRepository,
    timeout: int = 20,
    max_retries: int = 3,
    max_tokens: int = 65536,
):
    agent = create_agent(
        agent_strategy,
        model,
        verbose=verbose,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        max_tokens=max_tokens,
    )
    skill_block = render_skills(skill_repo)
    if not skill_block:
        return agent

    # All FHIR-AgentBench agents build each run from self.system_msg.
    # Patch that prompt once per sample so existing agent code stays unchanged.
    system_msg = copy.deepcopy(getattr(agent, "system_msg", []))
    if system_msg and isinstance(system_msg[0], dict):
        system_msg[0]["content"] = (
            str(system_msg[0].get("content", "")).rstrip()
            + "\n\n---\n"
            + skill_block
        )
        agent.system_msg = system_msg
    return agent


class LiteLLMAgent:
    """Small adapter exposing the .inference(history) API used by SkillUpdater."""

    def __init__(
        self,
        *,
        model: str,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 128000,
        timeout: int = 20,
        max_retries: int = 3,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

    def inference(self, history: List[Dict]) -> str:
        response, error, _usage = safe_llm_call(
            model=self.model,
            messages=history,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        if error:
            raise RuntimeError(error)
        if response is None:
            return ""
        if isinstance(response, dict):
            return str(response.get("content") or "")
        return str(getattr(response, "content", "") or "")


def serialize_message(message) -> Dict:
    if isinstance(message, dict):
        result = dict(message)
    elif hasattr(message, "model_dump"):
        result = message.model_dump(exclude_none=True)
    elif hasattr(message, "to_dict"):
        result = message.to_dict()
    else:
        result = {
            "role": getattr(message, "role", "assistant"),
            "content": getattr(message, "content", None),
        }

    # Make nested LiteLLM/OpenAI objects JSON-friendly.
    try:
        json.dumps(result, default=str)
        return result
    except TypeError:
        return json.loads(json.dumps(result, default=str))


def format_agent_actions(trace: List[Dict]) -> List[str]:
    actions: List[str] = []
    for msg in trace or []:
        role = msg.get("role")
        if role not in ("assistant", "agent"):
            continue
        content = msg.get("content")
        tool_calls = msg.get("tool_calls") or []
        if content:
            actions.append(str(content))
        for call in tool_calls:
            fn = call.get("function", {}) if isinstance(call, dict) else {}
            name = fn.get("name", "tool")
            args = fn.get("arguments", "")
            actions.append(f"TOOL {name} {args}")
    return actions
