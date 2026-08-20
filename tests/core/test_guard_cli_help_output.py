import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def _run_ps(cmd: str) -> str:
    return subprocess.check_output(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        cwd=ROOT,
        text=True,
        stderr=subprocess.STDOUT,
    )

def test_aurion_help_contains_required_commands():
    script = r'''
if (Test-Path ".\.venv\Scripts\python.exe") { $py = ".\.venv\Scripts\python.exe" } else { $py = "python" }

$g = @(
  "$env:LOCALAPPDATA\GitHubDesktop\app-*\resources\app\git\cmd\git.exe",
  "C:\Program Files\Git\cmd\git.exe",
  "C:\Program Files\Git\bin\git.exe",
  "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
) | ForEach-Object { Get-ChildItem $_ -ErrorAction SilentlyContinue } |
    Select-Object -Last 1 -ExpandProperty FullName
if ($g) { Set-Alias git $g }

. $PROFILE
aurion-help
'''
    out = _run_ps(script)
    required = [
        "aurion-safe-start",
        "aurion-status",
        "aurion-status-verbose",
        "aurion-paid-enable",
        "aurion-paid-30",
        "aurion-lock",
        "aurion-paid-disable",
        "aurion-panic-lock",
    ]
    for token in required:
        assert token in out
