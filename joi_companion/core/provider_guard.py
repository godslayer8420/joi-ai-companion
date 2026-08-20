"""Provider routing guard with explicit paid-model authorization window."""

from __future__ import annotations

import os
import time
from typing import Optional

LOCAL_PROVIDERS = {"ollama", "lmstudio", "local", "custom_local"}
PAID_AUTH_TOKEN_VALUE = "I_UNDERSTAND_PAID_COST"


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def is_local_provider(provider: Optional[str]) -> bool:
    return _norm(provider) in LOCAL_PROVIDERS


def has_paid_authorization(now: Optional[int] = None) -> bool:
    token = os.getenv("AURION_PAID_AUTH_TOKEN", "")
    if token != PAID_AUTH_TOKEN_VALUE:
        return False

    raw_exp = os.getenv("AURION_PAID_AUTH_EXPIRES_UNIX", "").strip()
    if not raw_exp:
        return False

    try:
        exp = int(raw_exp)
    except ValueError:
        return False

    now_ts = int(time.time()) if now is None else int(now)
    return exp > now_ts


def enforce_free_first_provider(provider: Optional[str], now: Optional[int] = None) -> str:
    candidate = _norm(provider) or "ollama"

    # Always allow local providers
    if is_local_provider(candidate):
        return candidate

    # Paid/non-local providers require explicit auth
    if has_paid_authorization(now=now):
        return candidate

    # Fail-closed to local
    return "ollama"
