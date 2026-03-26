import requests
import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SarvamResponse:
    content: str
    model: str = ""
    tokens_used: int = 0

    def __repr__(self) -> str:
        return f"SarvamResponse(content='{self.content[:50]}...', model='{self.model}')"


class SarvamLLM:
    API_BASE_URL = "https://api.sarvam.ai/v1"

    # ✅ FIXED MODELS
    AVAILABLE_MODELS = [
        "sarvam-m",
        "sarvam-30b",
        "sarvam-105b",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "sarvam-m",  # ✅ FIXED DEFAULT
        temperature: float = 0.5,
        max_tokens: int = 2000,
        timeout: int = 60,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")

        if not self.api_key:
            raise ValueError("SARVAM_API_KEY not found")

        if model not in self.AVAILABLE_MODELS:
            logger.warning(
                f"Model '{model}' invalid. Using 'sarvam-m' instead."
            )
            model = "sarvam-m"

        self.model = model
        self.temperature = max(0.0, min(1.0, temperature))
        self.max_tokens = max(1, min(4000, max_tokens))
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_url = f"{self.API_BASE_URL}/chat/completions"

        logger.info(
            f"Initialized SarvamLLM with model={self.model}, "
            f"temperature={self.temperature}"
        )

    def _prepare_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _prepare_payload(self, prompt: str) -> Dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": 0.95,
        }

    def _make_request(self, payload: Dict[str, Any]) -> requests.Response:
        headers = self._prepare_headers()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

                if not response.ok:
                    print("❌ Sarvam Response:", response.text)
                    response.raise_for_status()

                return response

            except requests.exceptions.HTTPError as e:
                last_error = str(e)

                # ❌ Don't retry 4xx errors
                if 400 <= e.response.status_code < 500:
                    raise

            except Exception as e:
                last_error = str(e)

            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)

        raise Exception(f"Sarvam API failed: {last_error}")

    def _extract_content(self, response: requests.Response):
        data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            raise Exception(f"Unexpected response format: {data}")

        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        return content, tokens_used

    def invoke(self, prompt: str) -> SarvamResponse:
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        logger.info(f"Calling Sarvam API (len={len(prompt)})")

        payload = self._prepare_payload(prompt)
        response = self._make_request(payload)
        content, tokens_used = self._extract_content(response)

        return SarvamResponse(
            content=content,
            model=self.model,
            tokens_used=tokens_used,
        )

    def __call__(self, prompt: str) -> SarvamResponse:
        return self.invoke(prompt)


# ✅ FIXED SINGLETON
_sarvam_instance: Optional[SarvamLLM] = None


def get_sarvam_llm(
    api_key: Optional[str] = None,
    model: str = "sarvam-m",  # ✅ FIXED
    temperature: float = 0.5,
    **kwargs
) -> SarvamLLM:
    global _sarvam_instance

    if _sarvam_instance is None:
        _sarvam_instance = SarvamLLM(
            api_key=api_key,
            model=model,
            temperature=temperature,
            **kwargs
        )

    return _sarvam_instance


def reset_sarvam_instance():
    global _sarvam_instance
    _sarvam_instance = None
