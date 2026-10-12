"""Tests for LibTrial configuration and LLM client initialization."""

import pytest
from libtrial.config import Settings, get_settings, DEFAULT_GEMMA_MODEL
from libtrial.llm_client import GemmaClient, ConfigurationError


def test_default_settings(monkeypatch):
    """Verify that default model and empty key behavior work as expected."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMMA_MODEL", raising=False)

    settings = get_settings()
    assert settings.gemini_api_key is None
    assert settings.has_api_key is False
    assert settings.gemma_model == DEFAULT_GEMMA_MODEL


def test_custom_settings(monkeypatch):
    """Verify that custom environment variables are parsed correctly."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-key-123")
    monkeypatch.setenv("GEMMA_MODEL", "custom-gemma-model")

    settings = get_settings()
    assert settings.gemini_api_key == "test-secret-key-123"
    assert settings.has_api_key is True
    assert settings.gemma_model == "custom-gemma-model"


def test_client_raises_on_missing_api_key():
    """GemmaClient must fail fast with a ConfigurationError if API key is missing."""
    empty_settings = Settings(gemini_api_key=None)
    with pytest.raises(ConfigurationError) as exc_info:
        GemmaClient(settings=empty_settings)

    assert "GEMINI_API_KEY is not set" in str(exc_info.value)
