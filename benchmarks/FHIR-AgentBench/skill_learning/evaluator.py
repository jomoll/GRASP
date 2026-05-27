import hashlib
import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from core_utils import get_litellm, is_reasoning_llm, safe_llm_call, setup_api_keys


class FHIRSampleEvaluator:
    def __init__(
        self,
        *,
        model: str,
        cache_path: Path,
        base_url: Optional[str] = None,
        timeout: int = 20,
        max_retries: int = 3,
        max_tokens: int = 65536,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, bool] = {}
        self._lock = threading.Lock()
        if self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.cache = {}
        setup_api_keys()

    def _cache_key(self, sample: Dict, answer: Optional[str], error: Optional[str]) -> str:
        payload = {
            "question_id": sample.get("question_id"),
            "question": sample.get("question"),
            "true_answer": sample.get("true_answer"),
            "answer": answer,
            "error": error,
            "model": self.model,
        }
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def score(self, sample: Dict, parsed_output: Dict) -> bool:
        answer = parsed_output.get("agent_answer")
        error = parsed_output.get("error")
        if error or answer is None:
            return False
        key = self._cache_key(sample, answer, error)
        with self._lock:
            if key in self.cache:
                return bool(self.cache[key])

        result = self._judge_answer(
            question=str(sample.get("question", "")),
            true_answer=str(sample.get("true_answer", "")),
            agent_answer=str(answer),
        )
        with self._lock:
            self.cache[key] = result
            self.cache_path.write_text(json.dumps(self.cache, indent=2), encoding="utf-8")
        return result

    def _judge_answer(self, *, question: str, true_answer: str, agent_answer: str) -> bool:
        normalized = re.sub(r"[^\w\s\[\].:-]", "", agent_answer).strip().lower()
        if normalized == re.sub(r"[^\w\s\[\].:-]", "", true_answer).strip().lower():
            return True

        prompt = f"""You evaluate answers for FHIR patient-data questions.

Return only 1 if the model answer is semantically correct, otherwise only 0.

Be lenient about formatting, brackets, units, and explanatory text when the value is correct.
For yes/no answers, [[1]] means yes and [[0]] means no.
For null/no-answer cases, accept a clear statement that no matching data was found.
For numeric answers, ignore harmless decimal formatting.
For date/time answers, ignore timezone and formatting differences when the date/time meaning matches.

Question: {question}
True answer: {true_answer}
Model answer: {agent_answer}

Return 1 or 0."""
        try:
            if self.model.startswith("vertex_ai/") and not self.base_url:
                msg, error, _usage = safe_llm_call(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_retries=self.max_retries,
                    timeout=self.timeout,
                    max_tokens=self.max_tokens,
                )
                if error:
                    raise RuntimeError(error)
                text = (msg.content or "").strip()
            else:
                litellm = get_litellm()
                for attempt in range(self.max_retries):
                    try:
                        response = litellm.completion(
                            model=self.model,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=None if is_reasoning_llm(self.model) else 0.0,
                            base_url=self.base_url,
                            custom_llm_provider="openai" if self.base_url else None,
                            api_key=os.getenv("OPENAI_API_KEY") if self.base_url else None,
                            timeout=self.timeout,
                        )
                        break
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise
                text = response.choices[0].message.content.strip()
            return text.startswith("1")
        except Exception as e:
            print(f"[FHIRSkillCycle] evaluator failed: {e}")
            return False
