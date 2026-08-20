import os
import sys
import time
from pathlib import Path

# Ensure repo root is importable when this script is run as: python scripts/check_provider_guard.py
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from joi_companion.core.provider_guard import enforce_free_first_provider, has_paid_authorization


def main() -> None:
    provider = os.getenv("AURION_LLM_PROVIDER", "")
    chosen = enforce_free_first_provider(provider)

    raw_exp = os.getenv("AURION_PAID_AUTH_EXPIRES_UNIX", "")
    now = int(time.time())
    try:
        exp = int(raw_exp) if raw_exp else None
    except ValueError:
        exp = None

    print(f"provider_env={provider or '<empty>'}")
    print(f"provider_chosen={chosen}")
    print(f"paid_token_set={'yes' if bool(os.getenv('AURION_PAID_AUTH_TOKEN')) else 'no'}")
    print(f"paid_auth_valid={'yes' if has_paid_authorization() else 'no'}")
    print(f"now_unix={now}")
    print(f"paid_exp_unix={exp if exp is not None else '<none>'}")
    print(f"seconds_remaining={(exp - now) if isinstance(exp, int) else '<none>'}")


if __name__ == "__main__":
    main()
