import os
import time

from joi_companion.core.provider_guard import (
    enforce_free_first_provider,
    has_paid_authorization,
    is_local_provider,
)


def _clear_env(monkeypatch):
    monkeypatch.delenv("AURION_PAID_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("AURION_PAID_AUTH_EXPIRES_UNIX", raising=False)


def test_local_provider_always_allowed(monkeypatch):
    _clear_env(monkeypatch)
    assert is_local_provider("ollama")
    assert enforce_free_first_provider("ollama") == "ollama"
    assert enforce_free_first_provider("lmstudio") == "lmstudio"


def test_paid_provider_blocked_without_token(monkeypatch):
    _clear_env(monkeypatch)
    assert enforce_free_first_provider("openai") == "ollama"
    assert enforce_free_first_provider("claude") == "ollama"


def test_paid_provider_blocked_with_bad_expiry(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AURION_PAID_AUTH_TOKEN", "I_UNDERSTAND_PAID_COST")
    monkeypatch.setenv("AURION_PAID_AUTH_EXPIRES_UNIX", "not-a-number")
    assert has_paid_authorization(now=1700000000) is False
    assert enforce_free_first_provider("openai", now=1700000000) == "ollama"


def test_paid_provider_blocked_when_expired(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AURION_PAID_AUTH_TOKEN", "I_UNDERSTAND_PAID_COST")
    monkeypatch.setenv("AURION_PAID_AUTH_EXPIRES_UNIX", "1699999999")
    assert has_paid_authorization(now=1700000000) is False
    assert enforce_free_first_provider("openai", now=1700000000) == "ollama"


def test_paid_provider_allowed_when_token_and_future_expiry(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("AURION_PAID_AUTH_TOKEN", "I_UNDERSTAND_PAID_COST")
    monkeypatch.setenv("AURION_PAID_AUTH_EXPIRES_UNIX", "1700003600")
    assert has_paid_authorization(now=1700000000) is True
    assert enforce_free_first_provider("openai", now=1700000000) == "openai"


def test_blank_provider_defaults_local(monkeypatch):
    _clear_env(monkeypatch)
    assert enforce_free_first_provider("") == "ollama"
    assert enforce_free_first_provider(None) == "ollama"
