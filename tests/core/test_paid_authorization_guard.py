import time

def test_paid_blocked_without_auth(monkeypatch):
    from joi_companion.core.personality_engine import enforce_free_first_provider
    monkeypatch.delenv("AURION_PAID_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("AURION_PAID_AUTH_EXPIRES_UNIX", raising=False)
    assert enforce_free_first_provider("anthropic") == "ollama"
    assert enforce_free_first_provider("openai") == "ollama"

def test_paid_blocked_with_bad_token(monkeypatch):
    from joi_companion.core.personality_engine import enforce_free_first_provider
    monkeypatch.setenv("AURION_PAID_AUTH_TOKEN", "WRONG")
    monkeypatch.setenv("AURION_PAID_AUTH_EXPIRES_UNIX", str(int(time.time()) + 600))
    assert enforce_free_first_provider("openai") == "ollama"

def test_paid_allowed_with_valid_window(monkeypatch):
    from joi_companion.core.personality_engine import enforce_free_first_provider
    monkeypatch.setenv("AURION_PAID_AUTH_TOKEN", "I_UNDERSTAND_PAID_COST")
    monkeypatch.setenv("AURION_PAID_AUTH_EXPIRES_UNIX", str(int(time.time()) + 600))
    assert enforce_free_first_provider("openai") == "openai"

def test_paid_denied_when_window_expired(monkeypatch):
    from joi_companion.core.personality_engine import enforce_free_first_provider
    monkeypatch.setenv("AURION_PAID_AUTH_TOKEN", "I_UNDERSTAND_PAID_COST")
    monkeypatch.setenv("AURION_PAID_AUTH_EXPIRES_UNIX", str(int(time.time()) - 1))
    assert enforce_free_first_provider("openai") == "ollama"

def test_local_provider_always_allowed(monkeypatch):
    from joi_companion.core.personality_engine import enforce_free_first_provider
    monkeypatch.delenv("AURION_PAID_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("AURION_PAID_AUTH_EXPIRES_UNIX", raising=False)
    assert enforce_free_first_provider("ollama") == "ollama"
    assert enforce_free_first_provider("custom_local") == "custom_local"
