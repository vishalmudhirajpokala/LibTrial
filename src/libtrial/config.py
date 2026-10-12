"""Configuration module for LibTrial."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

DEFAULT_GEMMA_MODEL = "gemma-4-26b-a4b-it"


@dataclass(frozen=True)
class Settings:
    gemini_api_key: Optional[str]
    gemma_model: str = DEFAULT_GEMMA_MODEL

    @property
    def has_api_key(self) -> bool:
        """Returns True if a non-empty API key is configured."""
        return bool(self.gemini_api_key and self.gemini_api_key.strip())


def get_settings() -> Settings:
    """Reads configuration from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMMA_MODEL", DEFAULT_GEMMA_MODEL).strip() or DEFAULT_GEMMA_MODEL
    return Settings(
        gemini_api_key=api_key.strip() if api_key else None,
        gemma_model=model,
    )
