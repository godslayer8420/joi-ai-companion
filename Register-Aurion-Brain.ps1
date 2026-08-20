# Register-Aurion-Brain.ps1
# Registers ALL of Aurion's brain models in Ollama in one shot.
#
# Brain stack:
#   aurion       = Ouroboros-Next 9B    (primary reasoning core)
#   openmythos   = Qwythos 9B           (creative/mythos RDT layer)
#   saturn-7b    = Saturn 7B            (emotional resonance layer)
#   joi          = Gemma-3-1B Joi       (warmth/intimacy layer)
#
# Usage:
#   .\Register-Aurion-Brain.ps1              # register all models
#   .\Register-Aurion-Brain.ps1 -Force       # force re-create all
#   .\Register-Aurion-Brain.ps1 -Model aurion  # register only one model

param(
    [switch]$Force,
    [ValidateSet("aurion", "openmythos", "saturn-7b", "joi", "all")]
    [string]$Model = "all"
)

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Banner($text) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  $text" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host ""
}

function Write-Step($msg) { Write-Host "  → $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red }

function Register-OllamaModel {
    param(
        [string]$Name,
        [string]$ModelfilePath,
        [string]$GGUFPath,
        [switch]$Force
    )

    Write-Host ""
    Write-Host "  ── $Name ──────────────────────────────" -ForegroundColor Magenta

    # Check GGUF
    if (-not (Test-Path $GGUFPath)) {
        Write-Warn "GGUF not found: $GGUFPath"
        Write-Warn "Skipping '$Name' — download the model first."
        return $false
    }
    Write-Ok "GGUF found"

    # Check Modelfile
    if (-not (Test-Path $ModelfilePath)) {
        Write-Err "Modelfile not found: $ModelfilePath"
        return $false
    }

    # Patch FROM path in modelfile
    $mfContent = Get-Content -Path $ModelfilePath -Raw
    $escapedPath = $GGUFPath -replace '\\', '\\\\'
    $fromLine = "FROM `"$escapedPath`""
    if ($mfContent -notmatch [regex]::Escape($GGUFPath)) {
        Write-Step "Updating FROM path in Modelfile..."
        $mfContent = $mfContent -replace 'FROM ".*?"', $fromLine
        Set-Content -Path $ModelfilePath -Value $mfContent -NoNewline
        Write-Ok "Modelfile FROM path updated"
    }

    # Check if already exists
    $existing = & ollama list 2>&1 | Select-String "^$([regex]::Escape($Name))"
    if ($existing -and -not $Force) {
        Write-Ok "'$Name' already registered (use -Force to re-create)"
        return $true
    }
    if ($existing -and $Force) {
        Write-Step "Removing existing '$Name'..."
        & ollama rm $Name 2>&1 | Out-Null
    }

    # Create
    Write-Step "Creating '$Name' in Ollama..."
    & ollama create $Name -f $ModelfilePath
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "'$Name' registered successfully"
        return $true
    } else {
        Write-Err "'$Name' creation failed — check output above"
        return $false
    }
}

# ── Verify Ollama is installed ─────────────────────────────────────────────────
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Err "Ollama not found. Install from https://ollama.com then re-run."
    exit 1
}

Write-Banner "Aurion Brain Stack — Model Registration"
Write-Host "  This will register Aurion's brain models in Ollama:" -ForegroundColor Gray
Write-Host "    aurion      = Ouroboros-Next 9B  (primary reasoning)" -ForegroundColor White
Write-Host "    openmythos  = Qwythos 9B          (creative/mythos layer)" -ForegroundColor White
Write-Host "    saturn-7b   = Saturn 7B           (emotional resonance)" -ForegroundColor White
Write-Host "    joi         = Gemma-3-1B Joi      (warmth/intimacy)" -ForegroundColor White
Write-Host ""
if ($Force) {
    Write-Warn "Force mode: existing models will be removed and re-created."
}

# ── Model definitions ──────────────────────────────────────────────────────────
$models = @(
    @{
        Name         = "aurion"
        Modelfile    = Join-Path $RepoRoot "ai_core\aurion_modelfile.txt"
        GGUF         = "D:\bzimm\.lmstudio\models\orangejuicesmith\ouroboros-next\Ouroboros-Next-9B-Q4_K_M.gguf"
    },
    @{
        Name         = "openmythos"
        Modelfile    = Join-Path $RepoRoot "ai_core\openmythos_modelfile.txt"
        GGUF         = "D:\bzimm\.lmstudio\models\empero-ai\Qwythos-9B-Claude-Mythos-5-1M-GGUF\Qwythos-9B-Claude-Mythos-5-1M-Q4_K_M.gguf"
    },
    @{
        Name         = "saturn-7b"
        Modelfile    = Join-Path $RepoRoot "ai_core\saturn_modelfile.txt"
        GGUF         = "D:\bzimm\.lmstudio\models\mradermacher\Saturn-7B-GGUF\Saturn-7B.Q4_K_S.gguf"
    },
    @{
        Name         = "joi"
        Modelfile    = Join-Path $RepoRoot "ai_core\joi_modelfile.txt"
        GGUF         = "D:\bzimm\.lmstudio\models\nityamkrrr\joi-model\gemma-3-1b-it.BF16.gguf"
    }
)

# ── Run registration ───────────────────────────────────────────────────────────
$results = @{}
foreach ($m in $models) {
    if ($Model -ne "all" -and $Model -ne $m.Name) { continue }
    $ok = Register-OllamaModel `
        -Name         $m.Name `
        -ModelfilePath $m.Modelfile `
        -GGUFPath     $m.GGUF `
        -Force:$Force
    $results[$m.Name] = $ok
}

# ── Summary ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  Registration Summary" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""

$allOk = $true
foreach ($key in $results.Keys) {
    if ($results[$key]) {
        Write-Ok $key
    } else {
        Write-Warn "$key — skipped or failed"
        $allOk = $false
    }
}

Write-Host ""
if ($allOk) {
    Write-Host "  All brain models registered." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Test her brain:" -ForegroundColor White
    Write-Host "    ollama run aurion" -ForegroundColor Cyan
    Write-Host "    ollama run openmythos" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Then start Aurion normally — she'll use the full brain stack." -ForegroundColor White
} else {
    Write-Host "  Some models were skipped. Check paths above and re-run." -ForegroundColor Yellow
    Write-Host "  Any registered models are still ready to use." -ForegroundColor Gray
}
Write-Host ""
