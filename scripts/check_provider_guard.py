import os
import time
from joi_companion.core.provider_guard import enforce_free_first_provider, has_paid_authorization

provider = os.getenv("AURION_LLM_PROVIDER", "")
chosen = enforce_free_first_provider(provider)

raw_exp = os.getenv("AURION_PAID_AUTH_EXPIRES_UNIX", "")
now = int(time.time())
exp = None
try:
    exp = int(raw_exp) if raw_exp else None
except Exception:
    exp = None

print("provider_env=", provider or "<empty>", sep="")
print("provider_chosen=", chosen, sep="")
print("paid_token_set=", "yes" if bool(os.getenv("AURION_PAID_AUTH_TOKEN")) else "no", sep="")
print("paid_auth_valid=", "yes" if has_paid_authorization() else "no", sep="")
print("now_unix=", now, sep="")
print("paid_exp_unix=", exp if exp is not None else "<none>", sep="")
print("seconds_remaining=", (exp - now) if isinstance(exp, int) else "<none>", sep="")
