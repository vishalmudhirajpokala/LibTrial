"""Gemma LLM client wrapper using the official google-genai SDK."""

from typing import Optional
from google import genai
from google.genai import errors, types

from libtrial.config import Settings, get_settings


class ConfigurationError(Exception):
    """Raised when required LLM configuration (such as GEMINI_API_KEY) is missing."""
    pass


class GemmaClient:
    """Minimal wrapper around Google GenAI client for Gemma models."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        if not self.settings.has_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY is not set or is empty. Please set it in your environment or .env file."
            )
        self._client = genai.Client(api_key=self.settings.gemini_api_key)

    @property
    def model_name(self) -> str:
        return self.settings.gemma_model

    def generate_text(self, prompt: str) -> str:
        """Generates plain text response using configured Gemma model."""
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model=self.settings.gemma_model,
                    contents=prompt,
                )
                return response.text or ""
            except errors.APIError as exc:
                msg = exc.message or ""
                if exc.code in (500, 502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                if exc.code == 404 or "not found" in msg.lower():
                    raise RuntimeError(
                        f"Google GenAI Error: Model '{self.settings.gemma_model}' was not found (HTTP 404). "
                        "If your API key does not have access to this Gemma model, set an alternate model "
                        "in your .env file (e.g. GEMMA_MODEL=gemini-2.5-flash or GEMMA_MODEL=gemini-2.0-flash)."
                    ) from exc
                if exc.code == 429 or "quota" in msg.lower():
                    raise RuntimeError(
                        f"Google GenAI Rate Limit / Quota Exceeded (HTTP 429): {msg}. Please retry in a few moments."
                    ) from exc
                raise RuntimeError(f"Google GenAI API Error (code {exc.code}): {msg}") from exc
            except Exception as exc:
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"Unexpected error communicating with Gemma API: {exc}") from exc
        return ""
