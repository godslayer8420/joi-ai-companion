import os
import time

from joi_companion.core.provider_guard import enforce_free_first_provider


def _clear():
    os.environ.pop("AURION_PAID_AUTH_TOKEN", None)
    os.environ.pop("AURION_PAID_AUTH_EXPIRES_UNIX", None)


def test_default_fail_closed_to_ollama():
    _clear()
    assert enforce_free_first_provider("openai") == "ollama"
    assert enforce_free_first_provider("claude") == "ollama"


def test_local_providers_always_allowed():
    _clear()
    assert enforce_free_first_provider("ollama") == "ollama"
    assert enforce_free_first_provider("lmstudio") == "lmstudio"
    assert enforce_free_first_provider("local") == "local"


def test_paid_provider_allowed_with_valid_window():
    _clear()
    os.environ["AURION_PAID_AUTH_TOKEN"] = "I_UNDERSTAND_PAID_COST"
    os.environ["AURION_PAID_AUTH_EXPIRES_UNIX"] = str(int(time.time()) + 600)
    assert enforce_free_first_provider("openai") == "openai"


def test_paid_provider_blocked_when_window_expires():
    _clear()
    os.environ["AURION_PAID_AUTH_TOKEN"] = "I_UNDERSTAND_PAID_COST"
    os.environ["AURION_PAID_AUTH_EXPIRES_UNIX"] = str(int(time.time()) - 1)
    assert enforce_free_first_provider("openai") == "ollama"
