param(
  [ValidateSet("unlock","lock","status")]
  [string]$Mode = "status",
  [int]$Minutes = 30,
  [string]$Provider = "openai"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (Test-Path ".\.venv\Scripts\python.exe") { $py = ".\.venv\Scripts\python.exe" } else { $py = "python" }

switch ($Mode) {
  "unlock" {
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $env:AURION_PAID_AUTH_TOKEN = "I_UNDERSTAND_PAID_COST"
    $env:AURION_PAID_AUTH_EXPIRES_UNIX = [string]($now + ($Minutes * 60))
    $env:AURION_LLM_PROVIDER = $Provider
    Write-Host "Unlocked paid provider '$Provider' for $Minutes minute(s)."
    & $py scripts/check_provider_guard.py
    break
  }
  "lock" {
    Remove-Item Env:AURION_PAID_AUTH_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:AURION_PAID_AUTH_EXPIRES_UNIX -ErrorAction SilentlyContinue
    $env:AURION_LLM_PROVIDER = "ollama"
    Write-Host "Relocked to local provider (ollama)."
    & $py scripts/check_provider_guard.py
    break
  }
  "status" {
    & $py scripts/check_provider_guard.py
    break
  }
}
