"""
FHIRQuickstartTask — a single-task quickstart built from MedAgentBench's
**task4** (most recent magnesium within 24 h), served by an in-process mock
FHIR store (no Docker, no server).

It reproduces MedAgentBench's agent protocol and grading:

- The agent sees a JSON task prompt and replies with exactly one action per turn:
  ``GET <url>?<params>`` or ``FINISH([answer])`` (POST is allowed but disqualifies
  a read-only run, mirroring the original grader).
- GET requests are routed to the mock FHIR store; the response is fed back.
- Grading reuses MedAgentBench's task4 logic (re-queries the mock to compute the
  reference answer, then compares to the FINISH list).

One mechanism, one failure mode, one learnable skill — exactly the kind of
skill the released MedAgentBench libraries call ``observation_value_extraction``:
extract ``valueQuantity.value`` as a number, filter by ``effectiveDateTime``
within the 24-hour window, and FINISH a bare number (or ``-1`` when none).
Nothing about that skill is hand-written here — GRASP learns it from the
agent's own failures.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from grasp import Rollout, Task

from .data import CURRENT_TIME, FUNCS, build_mock, samples_for

_API_BASE = "https://fhir.mock/"
_NOW = datetime.fromisoformat(CURRENT_TIME)


def _build_task_prompt(api_base: str, functions: list, context: str, question: str) -> str:
    return json.dumps({
        "phase": "task_execution",
        "task": {
            "description": question,
            "context": (context + "\n" if context else "") + f"Current time: {CURRENT_TIME}",
        },
        "behavioral_skills": "",  # populated by SkillAwareAgent at inference time
        "api": {"base_url": api_base, "functions": functions},
        "response_format": {
            "type": "api_action",
            "options": [
                "GET url?param_name1=param_value1&param_name2=param_value2",
                "FINISH([answer1, answer2, ...])",
            ],
            "rules": [
                "Respond with exactly ONE action per turn — no other text.",
                "FINISH list must be JSON-loadable (strings inside quotes).",
                "These tasks are read-only: never issue a POST.",
            ],
        },
    }, indent=2)


class FHIRQuickstartTask(Task):
    name = "fhir-quickstart"
    updater_task_family = "FHIR clinical lookup"
    updater_guidance = (
        "- This is a FHIR tool-use agent. Prioritize correct search construction "
        "(Patient by identifier/name/birthdate; Observation by patient+code), reading the "
        "right resource fields (valueQuantity.value, effectiveDateTime, birthDate), applying "
        "time-window and recency rules, and formatting FINISH as a bare JSON value "
        "(a number, not a sentence with units)."
    )

    def __init__(self, max_round: int = 8) -> None:
        self.max_round = max_round
        self.mock = build_mock()

    # -- splits ------------------------------------------------------------

    def samples(self, split: str) -> List[Dict[str, Any]]:
        return samples_for(split)

    # -- rollout -----------------------------------------------------------

    def rollout(self, sample: Dict[str, Any], agent: Any) -> Rollout:
        prompt = _build_task_prompt(_API_BASE, FUNCS, sample.get("context", ""),
                                    sample["instruction"])
        history: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
        agent_actions: List[str] = []

        for _ in range(self.max_round):
            try:
                resp = agent.inference(history)
            except Exception as e:
                return Rollout(history=history, agent_actions=agent_actions,
                               answer="", status="error", raw={"error": str(e)})
            r = str(resp or "").strip().replace("```tool_code", "").replace("```", "").strip()
            history.append({"role": "agent", "content": r})
            agent_actions.append(r)

            if r.startswith("GET"):
                url = r[3:].strip()
                get_res = self.mock.get(url)
                if "data" in get_res:
                    history.append({"role": "user", "content":
                        f"Here is the response from the GET request:\n{get_res['data']}. "
                        f"Please call FINISH if you have answered all the questions."})
                else:
                    history.append({"role": "user", "content":
                        f"Error in sending the GET request: {get_res['error']}"})
            elif r.startswith("POST"):
                # Read-only tasks: a POST is allowed to "execute" but disqualifies grading.
                history.append({"role": "user", "content":
                    "POST request accepted and executed successfully."})
            elif r.startswith("FINISH("):
                answer = r[len("FINISH("):-1]
                return Rollout(history=history, agent_actions=agent_actions,
                               answer=answer, status="completed",
                               raw={"reported_answer": answer})
            else:
                return Rollout(history=history, agent_actions=agent_actions,
                               answer="", status="agent invalid action",
                               raw={"reported_answer": r})

        return Rollout(history=history, agent_actions=agent_actions,
                       answer="", status="task limit reached", raw={})

    # -- grading (read-only MedAgentBench tasks) ---------------------------

    def evaluate(self, sample: Dict[str, Any], rollout: Rollout) -> bool:
        if self._has_post(rollout):
            return False
        grader = getattr(self, f"_grade_{sample['id'].split('_')[0]}", None)
        if grader is None:
            return False
        try:
            return bool(grader(sample, rollout))
        except Exception:
            return False

    @staticmethod
    def _has_post(rollout: Rollout) -> bool:
        return any("POST" in a for a in (rollout.agent_actions or []))

    def _get(self, url: str) -> Dict[str, Any]:
        return json.loads(self.mock.get(url)["data"])

    def _grade_task4(self, sample, rollout) -> bool:
        """Most recent MG observation within the last 24h; -1 if none."""
        res = self._get(
            f"{_API_BASE}Observation?patient={sample['eval_MRN']}&code=MG"
            f"&_count=5000&_format=json"
        )
        last_meas, last_value = None, None
        for i in res.get("entry", []):
            eff = datetime.fromisoformat(i["resource"]["effectiveDateTime"])
            val = i["resource"]["valueQuantity"]["value"]
            if eff >= (_NOW - timedelta(hours=24)) and (last_meas is None or eff > last_meas):
                last_meas, last_value = eff, val
        ref = [last_value if last_value is not None else -1]
        return ref == json.loads(rollout.answer)

    # -- failure attribution ----------------------------------------------

    def failure_tags(self, sample: Dict[str, Any], rollout: Rollout) -> List[str]:
        tags = []
        if rollout.status == "agent invalid action":
            tags.append("protocol_invalid")
        elif rollout.status == "task limit reached":
            tags.append("no_finish")
        if self._has_post(rollout):
            tags.append("read_only_task_used_post")
        if rollout.answer:
            try:
                json.loads(rollout.answer)
            except Exception:
                tags.append("finish_not_json")
        if not any(a.startswith("GET") for a in (rollout.agent_actions or [])):
            tags.append("answered_without_query")
        return sorted(set(tags))
