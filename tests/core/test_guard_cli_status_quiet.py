import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def _run(cmd):
    return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()

def test_aurion_status_single_line_contract():
    # Run in a fresh no-profile PowerShell to avoid local shell noise
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        r"""
$env:AURION_LLM_PROVIDER = "ollama"
Remove-Item Env:AURION_PAID_AUTH_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:AURION_PAID_AUTH_EXPIRES_UNIX -ErrorAction SilentlyContinue

if (Test-Path ".\.venv\Scripts\python.exe") { $py = ".\.venv\Scripts\python.exe" } else { $py = "python" }
$out = & $py .\scripts\check_provider_guard.py | Out-String
$lines = $out -split "`r?`n" | Where-Object { $_ -and $_.Contains("=") }
$map = @{}
foreach ($l in $lines) {
  $k,$v = $l -split "=",2
  $map[$k.Trim()] = $v.Trim()
}
Write-Host ("status: env={0} chosen={1} paid_valid={2} remaining={3}" -f `
  $map["provider_env"], $map["provider_chosen"], $map["paid_auth_valid"], $map["seconds_remaining"])
"""
    ]
    out = _run(cmd)
    assert re.match(r"^status: env=\S+ chosen=\S+ paid_valid=\S+ remaining=\S+$", out), out

def test_aurion_help_mentions_safe_ops():
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        r"""
Write-Host "Aurion Safe Ops"
Write-Host "aurion-safe-start"
Write-Host "aurion-status"
Write-Host "aurion-paid-enable"
Write-Host "aurion-paid-30"
Write-Host "aurion-lock"
Write-Host "aurion-paid-disable"
Write-Host "aurion-panic-lock"
"""
    ]
    out = _run(cmd)
    for token in [
        "Aurion Safe Ops",
        "aurion-safe-start",
        "aurion-status",
        "aurion-paid-enable",
        "aurion-paid-30",
        "aurion-lock",
        "aurion-paid-disable",
        "aurion-panic-lock",
    ]:
        assert token in out, out
