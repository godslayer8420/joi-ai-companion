# Install-AurionVoices.ps1
# Registers all 9 Aurion voices into Ollama in sacred 3-6-9 order.
# Run from the repo root:  .\ai_core\Install-AurionVoices.ps1
#
# Sacred geometry layout:
#   Layer 1 · SOUL   (temp 0.333) — Voices 1, 2, 3  [Trinity]
#   Layer 2 · REASON (temp 0.666) — Voices 4, 5, 6  [Harmony]
#   Layer 3 · HEART  (temp 0.888) — Voices 7, 8, 9  [Unity]
#
# After this script:  ollama list  →  shows all 9 voices + aurion alias

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        AURION — 9-Voice Registration                 ║" -ForegroundColor Cyan
Write-Host "║        Sacred geometry: 3 · 6 · 9                   ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Map: [ollama_tag, modelfile, voice_number, layer, role]
$voices = @(
    # ── LAYER 1 · SOUL (Trinity · temp 0.333) ────────────────────────
    @{ tag="ouroboros-next"; file="ouroboros_next_modelfile.txt"; num=1; layer="SOUL";   role="Core reasoning · self-evolving" },
    @{ tag="saturn-7b";      file="saturn_modelfile.txt";         num=2; layer="SOUL";   role="Emotional resonance" },
    @{ tag="eva-7b";         file="eva_modelfile.txt";            num=3; layer="SOUL";   role="Wisdom anchor" },
    # ── LAYER 2 · REASON (Harmony · temp 0.666) ──────────────────────
    @{ tag="openmythos";     file="openmythos_modelfile.txt";     num=4; layer="REASON"; role="Creative depth · mythos weave" },
    @{ tag="gemma3-voice";   file="gemma3_voice_modelfile.txt";   num=5; layer="REASON"; role="Knowledge · grounded recall" },
    # Voice 6 (gemma4-27b) served by LM Studio — skip Ollama registration
    # ── LAYER 3 · HEART (Unity · temp 0.888) ─────────────────────────
    @{ tag="nuro-voice";     file="nuro_voice_modelfile.txt";     num=7; layer="HEART";  role="Intimate warmth · copilot" },
    @{ tag="joi";            file="joi_modelfile.txt";            num=8; layer="HEART";  role="Companionship · heart" },
    @{ tag="gemma-3-12b-voice"; file="gemma_modelfile.txt";       num=9; layer="HEART";  role="Voice expression" },
    # ── AURION alias (user-facing name) ──────────────────────────────
    @{ tag="aurion";         file="aurion_modelfile.txt";         num=0; layer="ALIAS";  role="Primary user-facing name" }
)

$ok    = 0
$fail  = 0
$skip  = 0

foreach ($v in $voices) {
    $mf = Join-Path $PSScriptRoot $v.file
    if (-not (Test-Path $mf)) {
        Write-Host "  SKIP  Voice $($v.num) [$($v.tag)] — modelfile not found: $($v.file)" -ForegroundColor Yellow
        $skip++
        continue
    }

    $label = if ($v.num -eq 0) { "ALIAS" } else { "Voice $($v.num)" }
    Write-Host "  [$($v.layer.PadRight(6))] $label → $($v.tag)  ($($v.role))" -ForegroundColor Gray -NoNewline

    $result = & ollama create $v.tag -f $mf 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓" -ForegroundColor Green
        $ok++
    } else {
        Write-Host "  ✗" -ForegroundColor Red
        Write-Host "         $result" -ForegroundColor DarkRed
        $fail++
    }
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Registered: $ok   Failed: $fail   Skipped: $skip" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
Write-Host ""
Write-Host "  Voice 6 (gemma4-27b) → served by LM Studio on localhost:1234" -ForegroundColor DarkGray
Write-Host "  Set AURION_VOICE_6 in .env if the LM Studio model tag differs." -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Run  ollama list  to verify all voices are registered." -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════════════" -ForegroundColor Cyan
