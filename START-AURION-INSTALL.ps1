# START-AURION-INSTALL.ps1  (ASCII-safe)
# Double-click this OR run from ANY directory in PowerShell.
# Finds the repo automatically and installs all 9 Aurion voices.

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Host ""
Write-Host "  Repo: $repoRoot" -ForegroundColor DarkCyan
Write-Host ""

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "  ERROR: Ollama not found in PATH." -ForegroundColor Red
    Write-Host "  Download from: https://ollama.com/download" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

& "$repoRoot\ai_core\Install-AurionVoices.ps1"

Write-Host ""
Write-Host "  Done. Verify with:  ollama list" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to close"
