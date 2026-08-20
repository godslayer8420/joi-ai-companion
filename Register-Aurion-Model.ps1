# Register-Aurion-Model.ps1
# Creates the "aurion" model in Ollama from ai_core/aurion_modelfile.txt
# After this runs: ollama run aurion  — that's it.
#
# Usage:
#   .\Register-Aurion-Model.ps1           # register aurion
#   .\Register-Aurion-Model.ps1 -Force    # force re-create if already exists
#   .\Register-Aurion-Model.ps1 -GGUFPath "D:\MyModels\my-model.gguf"  # custom base model

param(
    [switch]$Force,
    [string]$GGUFPath = "D:\bzimm\.lmstudio\models\orangejuicesmith\ouroboros-next\Ouroboros-Next-9B-Q4_K_M.gguf"
)

$RepoRoot   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Modelfile  = Join-Path $RepoRoot "ai_core\aurion_modelfile.txt"
$ModelName  = "aurion"

function Write-Step($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  Registering Aurion in Ollama" -ForegroundColor White
Write-Host "  Model name: aurion" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""

# --- Check Ollama is installed ---
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Err "Ollama not found. Install from https://ollama.com then re-run this script."
    exit 1
}

# --- Verify GGUF exists ---
if (-not (Test-Path $GGUFPath)) {
    Write-Err "Base GGUF not found at: $GGUFPath"
    Write-Host "  Either download the model there, or pass -GGUFPath to specify a different GGUF." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Alternative: use any Ollama model as the base instead." -ForegroundColor Gray
    Write-Host "  Edit ai_core\aurion_modelfile.txt and change the FROM line to:" -ForegroundColor Gray
    Write-Host "    FROM llama3.1" -ForegroundColor Gray
    Write-Host "  Then re-run this script." -ForegroundColor Gray
    exit 1
}

Write-Ok "GGUF found: $GGUFPath"

# --- Patch Modelfile with actual GGUF path (in case it differs) ---
$mfContent = Get-Content -Path $Modelfile -Raw
$escapedPath = $GGUFPath -replace '\\', '\\\\'
if ($mfContent -notmatch [regex]::Escape($GGUFPath)) {
    Write-Step "Patching Modelfile FROM path..."
    $mfContent = $mfContent -replace 'FROM ".*?"', "FROM `"$escapedPath`""
    Set-Content -Path $Modelfile -Value $mfContent -NoNewline
    Write-Ok "Modelfile updated."
}

# --- Check if aurion already exists ---
$existing = & ollama list 2>&1 | Select-String "^aurion"
if ($existing -and -not $Force) {
    Write-Host ""
    Write-Host "  ℹ  'aurion' model already exists in Ollama." -ForegroundColor Yellow
    Write-Host "     To test it now:  ollama run aurion" -ForegroundColor White
    Write-Host "     To re-create it: .\Register-Aurion-Model.ps1 -Force" -ForegroundColor Gray
    Write-Host ""
    exit 0
}

if ($existing -and $Force) {
    Write-Step "Removing existing 'aurion' model..."
    & ollama rm aurion 2>&1 | Out-Null
}

# --- Create the model ---
Write-Step "Creating 'aurion' model (this may take a minute)..."
Write-Host ""

& ollama create $ModelName -f $Modelfile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Ok "'aurion' model created successfully."
    Write-Host ""
    Write-Host "  You can now run her with:" -ForegroundColor White
    Write-Host "    ollama run aurion" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Or start Aurion normally — she'll use 'aurion' automatically." -ForegroundColor White
    Write-Host "  (AURION_LLM_MODEL=aurion is already set in .env)" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Err "Ollama create failed. Check the output above for details."
    exit 1
}
