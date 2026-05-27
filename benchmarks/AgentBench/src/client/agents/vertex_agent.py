"""
Vertex AI Gemini Agent for AgentBench

Uses Google Cloud authentication (application default credentials or service account)
to automatically manage OAuth2 tokens for Vertex AI API calls.
"""

import json
import time
import requests
from typing import List, Dict, Any, Optional

from ..agent import AgentClient

# Try to import google-auth, provide helpful error if not installed
try:
    import google.auth
    import google.auth.transport.requests
    from google.oauth2 import service_account
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False


class VertexAgent(AgentClient):
    """
    Agent client for Vertex AI Gemini models with automatic OAuth2 authentication.

    Authentication methods (in order of precedence):
    1. Service account key file (if service_account_file is provided)
    2. Application Default Credentials (gcloud auth application-default login)
    3. Environment's default credentials (GCE, Cloud Run, etc.)

    Usage in config:
        module: src.client.agents.VertexAgent
        parameters:
            project_id: "your-project-id"
            location: "us-central1"
            model: "gemini-2.0-flash"
    """

    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model: str = "gemini-2.0-flash",
        service_account_file: Optional[str] = None,
        temperature: float = 0,
        max_output_tokens: int = 8192,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        if not GOOGLE_AUTH_AVAILABLE:
            raise ImportError(
                "google-auth library is required for VertexAIAgent. "
                "Install it with: pip install google-auth google-auth-httplib2"
            )

        self.project_id = project_id
        self.location = location
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

        # Initialize credentials
        if service_account_file:
            self.credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=self.SCOPES
            )
        else:
            # Use application default credentials
            self.credentials, _ = google.auth.default(scopes=self.SCOPES)

        # Request object for token refresh
        self._auth_request = google.auth.transport.requests.Request()

        # Build endpoint URL
        self.endpoint = (
            f"https://aiplatform.googleapis.com/v1/projects/{project_id}"
            f"/locations/{location}/publishers/google/models/{model}:generateContent"
        )

    def _get_auth_header(self) -> Dict[str, str]:
        """Get authorization header, refreshing token if needed."""
        # Refresh credentials if expired
        if not self.credentials.valid:
            self.credentials.refresh(self._auth_request)

        return {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json"
        }

    @staticmethod
    def _openai_tools_to_gemini(tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        declarations = []
        for tool in tools:
            if tool.get("type") != "function":
                continue
            function = dict(tool.get("function", {}))
            if "parameters" in function:
                function["parameters"] = dict(function["parameters"])
            declarations.append(function)
        if not declarations:
            return None
        return [{"functionDeclarations": declarations}]

    def _format_messages(
        self,
        history: List[dict],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Convert AgentBench message format to Vertex AI Gemini format."""
        role_map = {
            "user": "user",
            "agent": "model",
            "assistant": "model",
        }

        contents = []
        system_parts = []
        tool_call_names = {}
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content")

            if role == "system":
                if content:
                    system_parts.append({"text": str(content)})
                continue

            if role in ("assistant", "agent") and msg.get("tool_calls"):
                parts = []
                if content:
                    parts.append({"text": str(content)})
                call_summaries = []
                for tool_call in msg.get("tool_calls") or []:
                    function = tool_call.get("function", {})
                    name = function.get("name", "")
                    if tool_call.get("id") and name:
                        tool_call_names[tool_call["id"]] = name
                    call_summaries.append(
                        f"Called tool {name} with arguments {function.get('arguments') or '{}'}."
                    )
                if call_summaries:
                    parts.append({"text": "\n".join(call_summaries)})
                contents.append({"role": "model", "parts": parts})
                continue

            if role == "tool":
                call_id = msg.get("tool_call_id", "")
                name = msg.get("name") or tool_call_names.get(call_id, "tool")
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"Tool result from {name}: {content or ''}"}],
                })
                continue

            contents.append({
                "role": role_map.get(role, "user"),
                "parts": [{"text": str(content or "")}]
            })

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens
            }
        }
        if system_parts:
            body["systemInstruction"] = {"parts": system_parts}
        gemini_tools = self._openai_tools_to_gemini(tools)
        if gemini_tools:
            body["tools"] = gemini_tools
        return body

    @staticmethod
    def _parse_response_message(result: Dict[str, Any]):
        parts = result["candidates"][0]["content"].get("parts", [])
        text_parts = []
        tool_calls = []
        for idx, part in enumerate(parts):
            if "text" in part:
                text_parts.append(part["text"])
            if "functionCall" in part:
                function_call = part["functionCall"]
                name = function_call.get("name", "")
                args = function_call.get("args", {})
                tool_calls.append({
                    "id": f"call_vertex_{idx}",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(args),
                    },
                })
        content = "\n".join(text_parts)
        if tool_calls:
            return {"role": "assistant", "content": content or None, "tool_calls": tool_calls}
        return content

    def inference(self, history: List[dict], tools: Optional[List[Dict[str, Any]]] = None):
        """
        Run inference on the Vertex AI Gemini model.

        Args:
            history: List of message dicts with 'role' and 'content' keys

        Returns:
            Model response text
        """
        max_retries = 6
        base_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                headers = self._get_auth_header()
                body = self._format_messages(history, tools=tools)

                resp = requests.post(
                    self.endpoint,
                    json=body,
                    headers=headers,
                    timeout=300
                )

                if resp.status_code == 429:
                    # Rate limit - use exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt), 60)  # Cap at 1 minute
                    jitter = delay * 0.2 * (0.5 - time.time() % 1)  # Add some randomness
                    wait_time = delay + jitter
                    print(f"Rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue

                if resp.status_code != 200:
                    error_text = resp.text.lower()
                    # Check for context limit errors
                    if any(word in error_text for word in ["token", "limit", "exceed", "context"]):
                        from src.client.agent import AgentContextLimitException
                        raise AgentContextLimitException(resp.text)
                    raise Exception(f"API error {resp.status_code}: {resp.text}")

                result = resp.json()

                return self._parse_response_message(result)

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"Warning (attempt {attempt + 1}): {e}")
                time.sleep(base_delay * (attempt + 1))

        raise Exception(f"Failed after {max_retries} attempts")
