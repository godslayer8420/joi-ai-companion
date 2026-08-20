# START-AURION-INSTALL.ps1
# ─────────────────────────────────────────────────────────────────
# Double-click this file OR run from ANY directory in PowerShell.
# It finds the repo automatically and installs all 9 Aurion voices.
# ─────────────────────────────────────────────────────────────────

# Always work relative to THIS script's location (the repo root)
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Host ""
Write-Host "  Repo: $repoRoot" -ForegroundColor DarkCyan
Write-Host ""

# Check Ollama is installed
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "  ERROR: Ollama not found in PATH." -ForegroundColor Red
    Write-Host "  Download from: https://ollama.com/download" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Run the voice installer
& "$repoRoot\ai_core\Install-AurionVoices.ps1"

Write-Host ""
Write-Host "  Done. Verify with:  ollama list" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
