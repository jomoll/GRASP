"""
Vertex AI Gemini Agent for MedAgentBench

Uses Google Cloud authentication (application default credentials or service account)
to automatically manage OAuth2 tokens for Vertex AI API calls.
"""

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

    def _format_messages(self, history: List[dict]) -> Dict[str, Any]:
        """Convert MedAgentBench message format to Vertex AI Gemini format."""
        role_map = {
            "user": "user",
            "agent": "model",
        }

        system_parts = []
        contents = []
        for msg in history:
            role = msg["role"]
            if role == "system":
                system_parts.append({"text": msg["content"]})
            else:
                contents.append({
                    "role": role_map.get(role, "user"),
                    "parts": [{"text": msg["content"]}]
                })

        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens
            }
        }
        if system_parts:
            body["systemInstruction"] = {"parts": system_parts}
        return body

    def inference(self, history: List[dict]) -> str:
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
                body = self._format_messages(history)

                resp = requests.post(
                    self.endpoint,
                    json=body,
                    headers=headers,
                    timeout=120
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

                # Extract text from Gemini response format
                return result["candidates"][0]["content"]["parts"][0]["text"]

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"Warning (attempt {attempt + 1}): {e}")
                time.sleep(base_delay * (attempt + 1))

        raise Exception(f"Failed after {max_retries} attempts")
