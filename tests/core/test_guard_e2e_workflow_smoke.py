import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = Path(sys.executable)

def _run_cmd(args):
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()

def test_guard_status_script_runs_and_has_required_fields():
    out = _run_cmd([str(PY), "scripts/check_provider_guard.py"])
    lines = [x for x in out.splitlines() if "=" in x]
    keys = {ln.split("=", 1)[0].strip() for ln in lines}

    required = {
        "provider_env",
        "provider_chosen",
        "paid_token_set",
        "paid_auth_valid",
        "now_unix",
        "paid_exp_unix",
        "seconds_remaining",
    }
    assert required.issubset(keys), f"missing keys: {required - keys}\n{out}"

def test_set_paid_auth_status_mode_runs():
    ps = ROOT / "scripts" / "set_paid_auth.ps1"
    out = _run_cmd(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps),
            "-Mode",
            "status",
        ]
    )
    assert "provider_env=" in out
    assert "provider_chosen=" in out
