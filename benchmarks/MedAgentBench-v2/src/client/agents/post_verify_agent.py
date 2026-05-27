"""
PostVerifyingAgent — wraps any AgentClient and injects a GET-after-POST
verification step into the conversation history before each inference call.

When the most recent user message is a POST acceptance ("POST request accepted
and executed successfully..."), this wrapper:

  1. Parses the POST URL from the preceding agent message to extract the
     resource type (e.g. Observation, MedicationRequest, ServiceRequest).
  2. Extracts the patient MRN from the POST body's subject.reference field.
  3. Performs a GET on the stored resource (most recent, filtered by patient).
  4. Appends the GET response as an extra user message to the history.
  5. Passes the augmented history to the inner agent.

The task server never sees the injected message — it only exists in the
history slice passed to inference(). This means:
  - Task execution, round counting, and evaluation are completely unchanged.
  - Baseline agents do not get this feedback.
  - The skill-learning agent can observe POST results and write skills that
    encode the correct resource structure.

Chain order: PostVerifyingAgent → SkillAwareAgent → BaseAgent
"""

import json
import re
import requests
from typing import List, Optional, Tuple

from ..agent import AgentClient

_POST_ACCEPTED_PREFIX = "POST request accepted and executed successfully"

# Resource types we know how to verify, and the query parameter to filter by patient
_VERIFIABLE_RESOURCES = {
    "Observation":       "patient",
    "MedicationRequest": "patient",
    "ServiceRequest":    "patient",
}


def _parse_post_from_history(history: List[dict]) -> Optional[Tuple[str, str, str]]:
    """
    Scan backwards through history to find the most recent POST agent message
    that preceded the current POST-accepted user message.

    Returns (resource_type, mrn, fhir_base) or None if unparseable.
    """
    # Walk backwards looking for the agent POST message
    for msg in reversed(history[:-1]):  # skip last (the POST-accepted user msg)
        if msg.get("role") != "agent":
            continue
        content = msg.get("content", "").strip()
        if not content.startswith("POST"):
            continue

        lines = content.split("\n", 1)
        post_url = lines[0][4:].strip()  # strip "POST "

        # Extract resource type from URL path
        # e.g. http://localhost:8080/fhir/Observation → Observation
        match = re.search(r"/fhir/(\w+)", post_url)
        if not match:
            return None
        resource_type = match.group(1)

        if resource_type not in _VERIFIABLE_RESOURCES:
            return None

        # Extract FHIR base URL (everything up to /ResourceType)
        fhir_base = post_url[: post_url.rfind(f"/{resource_type}")] + "/"

        # Extract patient MRN from POST body
        mrn = None
        if len(lines) > 1:
            try:
                body = json.loads(lines[1])
                subject_ref = (
                    body.get("subject", {}).get("reference", "")
                    or body.get("patient", {}).get("reference", "")
                )
                # reference is like "Patient/S1234567" or just "S1234567"
                mrn = subject_ref.split("/")[-1] if subject_ref else None
            except (json.JSONDecodeError, AttributeError):
                pass

        return resource_type, mrn, fhir_base

    return None


def _fetch_stored_resource(resource_type: str, mrn: Optional[str],
                           fhir_base: str) -> str:
    """Retrieve the most recently stored resource and return a formatted string."""
    patient_param = _VERIFIABLE_RESOURCES[resource_type]
    params = {"_sort": "-_lastUpdated", "_count": "1", "_format": "json"}
    if mrn:
        params[patient_param] = mrn
    else:
        # Without a patient filter the result is too ambiguous — skip
        return f"[POST verification] Could not verify {resource_type} — patient reference missing from POST body."

    url = f"{fhir_base}{resource_type}"
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            entries = data.get("entry", [])
            if entries:
                resource = entries[0].get("resource", {})
                return (
                    f"[POST verification — for your information only, do not POST again "
                    f"unless the task explicitly requires another POST] "
                    f"The {resource_type} resource was stored successfully. "
                    f"Here is what was actually saved to the FHIR server:\n"
                    f"{json.dumps(resource, indent=2)}"
                )
            else:
                return (
                    f"[POST verification — for your information only] Warning: the "
                    f"{resource_type} POST was accepted but no matching resource was "
                    f"found on retrieval. The resource may not have been stored correctly."
                )
        else:
            return (
                f"[POST verification] Could not retrieve stored {resource_type} "
                f"(HTTP {resp.status_code})."
            )
    except Exception as e:
        return f"[POST verification] GET request failed: {e}"


class PostVerifyingAgent(AgentClient):
    """
    Wraps any AgentClient (typically SkillAwareAgent) with GET-after-POST
    verification, injected only into the local history slice — the task
    server and evaluation pipeline are untouched.
    """

    def __init__(self, agent: AgentClient) -> None:
        super().__init__()
        self.agent = agent

    def inference(self, history: List[dict]) -> str:
        augmented = list(history)

        # Check if the last user message is a POST acceptance
        if history:
            last = history[-1]
            if (last.get("role") == "user"
                    and last.get("content", "").startswith(_POST_ACCEPTED_PREFIX)):

                parsed = _parse_post_from_history(history)
                if parsed:
                    resource_type, mrn, fhir_base = parsed
                    verification_msg = _fetch_stored_resource(
                        resource_type, mrn, fhir_base
                    )
                    augmented.append({
                        "role": "user",
                        "content": verification_msg,
                    })

        return self.agent.inference(augmented)
